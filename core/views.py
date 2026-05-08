from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.db import models, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.db import IntegrityError
from django.db.models import Count

from core.models import (
    User, Workspace, WorkspaceMembership, WorkspaceInvitation,
    Channel, ChannelMembership, ChannelInvitation, Message, MessageReaction,
)

EMOJI_SET = ['👍', '👎', '❤️', '😂', '🎉', '🔥']
from core.auth import login_required, get_current_user


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def register(request):
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        password = request.POST.get('password', '')

        error = None
        if not all([email, username, nickname, password]):
            error = 'All fields are required.'
        elif User.objects.filter(email=email).exists():
            error = 'An account with that email already exists.'
        elif User.objects.filter(username=username).exists():
            error = 'That username is already taken.'

        if error:
            return render(request, 'core/register.html', {'error': error})

        user = User.objects.create(
            email=email,
            username=username,
            nickname=nickname,
            password_hash=make_password(password),
        )
        # Link any pending workspace invitations sent to this email
        WorkspaceInvitation.objects.filter(
            invitee_email=email, invitee_user__isnull=True
        ).update(invitee_user=user)

        request.session['user_id'] = user.user_id
        request.session['username'] = user.username
        return redirect('dashboard')

    return render(request, 'core/register.html')


def login(request):
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password   = request.POST.get('password', '')

        user = (
            User.objects.filter(username=identifier).first()
            or User.objects.filter(email=identifier).first()
        )

        if user and check_password(password, user.password_hash):
            request.session['user_id'] = user.user_id
            request.session['username'] = user.username
            return redirect('dashboard')

        return render(request, 'core/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'core/login.html')


def logout(request):
    request.session.flush()
    return redirect('login')


# ---------------------------------------------------------------------------
# Dashboard + profile
# ---------------------------------------------------------------------------

def dashboard(request):
    if not request.session.get('user_id'):
        return render(request, 'core/home.html')

    user = get_current_user(request)
    memberships = (
        WorkspaceMembership.objects
        .filter(user=user)
        .select_related('workspace')
        .order_by('workspace__name')
    )
    pending_count = WorkspaceInvitation.objects.filter(
        invitee_user=user, accepted=False
    ).count()
    return render(request, 'core/dashboard.html', {
        'user': user,
        'memberships': memberships,
        'pending_count': pending_count,
    })


@login_required
def profile(request):
    user = get_current_user(request)
    ctx = {'user': user}

    if request.method == 'POST':
        if 'nickname' in request.POST:
            nickname = request.POST.get('nickname', '').strip()
            if nickname:
                user.nickname = nickname
                user.save(update_fields=['nickname', 'updated_at'])
                ctx['nickname_success'] = True

        elif 'new_password' in request.POST:
            current  = request.POST.get('current_password', '')
            new_pw   = request.POST.get('new_password', '')
            confirm  = request.POST.get('confirm_password', '')

            if not check_password(current, user.password_hash):
                ctx['pw_error'] = 'Current password is incorrect.'
            elif len(new_pw) < 6:
                ctx['pw_error'] = 'New password must be at least 6 characters.'
            elif new_pw != confirm:
                ctx['pw_error'] = 'Passwords do not match.'
            else:
                user.password_hash = make_password(new_pw)
                user.save(update_fields=['password_hash', 'updated_at'])
                ctx['pw_success'] = True

    return render(request, 'core/profile.html', ctx)


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

@login_required
def workspace_new(request):
    user = get_current_user(request)

    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            return render(request, 'core/workspace_new.html', {'error': 'Name is required.'})

        with transaction.atomic():
            workspace = Workspace.objects.create(
                name=name,
                description=description or None,
                created_by=user,
            )
            WorkspaceMembership.objects.create(
                workspace=workspace,
                user=user,
                role='admin',
            )

        return redirect('workspace', workspace_id=workspace.workspace_id)

    return render(request, 'core/workspace_new.html')


@login_required
def workspace(request, workspace_id):
    user      = get_current_user(request)
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    membership = WorkspaceMembership.objects.filter(
        workspace=workspace, user=user
    ).first()
    if not membership:
        return render(request, 'core/403.html', status=403)

    is_admin = membership.role == 'admin'
    members  = (
        WorkspaceMembership.objects
        .filter(workspace=workspace)
        .select_related('user')
        .order_by('user__username')
    )

    return render(request, 'core/workspace.html', {
        'user':      user,
        'workspace': workspace,
        'members':   members,
        'is_admin':  is_admin,
    })


@login_required
def workspace_invite(request, workspace_id):
    user      = get_current_user(request)
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    membership = WorkspaceMembership.objects.filter(
        workspace=workspace, user=user, role='admin'
    ).first()
    if not membership:
        return render(request, 'core/403.html', status=403)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            return render(request, 'core/workspace_invite.html',
                          {'workspace': workspace, 'error': 'Email is required.'})

        # Don't invite someone already a member
        invitee_user = User.objects.filter(email=email).first()
        if invitee_user and WorkspaceMembership.objects.filter(
            workspace=workspace, user=invitee_user
        ).exists():
            return render(request, 'core/workspace_invite.html',
                          {'workspace': workspace, 'error': 'That user is already a member.'})

        # Don't create a duplicate pending invitation
        if WorkspaceInvitation.objects.filter(
            workspace=workspace, invitee_email=email, accepted=False
        ).exists():
            return render(request, 'core/workspace_invite.html',
                          {'workspace': workspace, 'error': 'A pending invitation for that email already exists.'})

        WorkspaceInvitation.objects.create(
            workspace=workspace,
            invited_by=user,
            invitee_user=invitee_user,
            invitee_email=email,
        )
        return render(request, 'core/workspace_invite.html',
                      {'workspace': workspace, 'success': f'Invitation sent to {email}.'})

    return render(request, 'core/workspace_invite.html', {'workspace': workspace})


@login_required
def invitations(request):
    user = get_current_user(request)
    pending = (
        WorkspaceInvitation.objects
        .filter(invitee_user=user, accepted=False)
        .select_related('workspace', 'invited_by')
        .order_by('-invited_at')
    )
    return render(request, 'core/invitations.html', {'user': user, 'pending': pending})


@login_required
def invitation_accept(request, invitation_id):
    user       = get_current_user(request)
    invitation = get_object_or_404(WorkspaceInvitation, pk=invitation_id, invitee_user=user, accepted=False)

    with transaction.atomic():
        WorkspaceMembership.objects.get_or_create(
            workspace=invitation.workspace,
            user=user,
            defaults={'role': 'member'},
        )
        invitation.accepted    = True
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted', 'accepted_at'])

    return redirect('workspace', workspace_id=invitation.workspace.workspace_id)


@login_required
def invitation_decline(request, invitation_id):
    user       = get_current_user(request)
    invitation = get_object_or_404(WorkspaceInvitation, pk=invitation_id, invitee_user=user, accepted=False)
    invitation.delete()
    return redirect('invitations')


@login_required
def member_remove(request, workspace_id, user_id):
    current_user = get_current_user(request)
    workspace    = get_object_or_404(Workspace, pk=workspace_id)

    # Must be admin
    if not WorkspaceMembership.objects.filter(
        workspace=workspace, user=current_user, role='admin'
    ).exists():
        return render(request, 'core/403.html', status=403)

    # Can't remove yourself
    if current_user.user_id == user_id:
        return redirect('workspace', workspace_id=workspace_id)

    WorkspaceMembership.objects.filter(workspace=workspace, user_id=user_id).delete()
    return redirect('workspace', workspace_id=workspace_id)


@login_required
def member_promote(request, workspace_id, user_id):
    current_user = get_current_user(request)
    workspace    = get_object_or_404(Workspace, pk=workspace_id)

    if not WorkspaceMembership.objects.filter(
        workspace=workspace, user=current_user, role='admin'
    ).exists():
        return render(request, 'core/403.html', status=403)

    WorkspaceMembership.objects.filter(
        workspace=workspace, user_id=user_id
    ).update(role='admin')
    return redirect('workspace', workspace_id=workspace_id)


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

def _get_workspace_role(user, workspace):
    """Return the user's WorkspaceMembership or None."""
    return WorkspaceMembership.objects.filter(workspace=workspace, user=user).first()


def _is_channel_member(user, channel):
    return ChannelMembership.objects.filter(channel=channel, user=user).exists()


@login_required
def channel_list(request, workspace_id):
    user      = get_current_user(request)
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    if not _get_workspace_role(user, workspace):
        return render(request, 'core/403.html', status=403)

    member_channel_ids = ChannelMembership.objects.filter(user=user).values_list('channel_id', flat=True)

    # Public channels in this workspace + private/direct ones the user belongs to
    channels = Channel.objects.filter(workspace=workspace).filter(
        models.Q(channel_type='public') | models.Q(channel_id__in=member_channel_ids)
    ).order_by('channel_type', 'name')

    pending_invites = ChannelInvitation.objects.filter(
        invitee_user=user, accepted=False, channel__workspace=workspace
    ).select_related('channel', 'invited_by')

    return render(request, 'core/channel_list.html', {
        'user':           user,
        'workspace':      workspace,
        'channels':       channels,
        'member_ids':     set(member_channel_ids),
        'pending_invites': pending_invites,
    })


@login_required
def workspace_members_search(request, workspace_id):
    user      = get_current_user(request)
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    if not _get_workspace_role(user, workspace):
        return JsonResponse([], safe=False)

    q = request.GET.get('q', '').strip()
    qs = (
        User.objects
        .filter(workspacemembership__workspace=workspace)
        .exclude(user_id=user.user_id)
    )
    if q:
        qs = qs.filter(
            models.Q(username__icontains=q) | models.Q(nickname__icontains=q)
        )
    data = [{'username': m.username, 'nickname': m.nickname} for m in qs[:10]]
    return JsonResponse(data, safe=False)


@login_required
def channel_new(request, workspace_id):
    user      = get_current_user(request)
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    if not _get_workspace_role(user, workspace):
        return render(request, 'core/403.html', status=403)

    if request.method == 'POST':
        channel_type = request.POST.get('channel_type', 'public')
        other_user   = request.POST.get('dm_username', '').strip()

        error      = None
        dm_target  = None

        if channel_type == 'direct':
            if not other_user:
                error = 'Enter the username of the person you want to DM.'
            else:
                dm_target = User.objects.filter(username=other_user).first()
                if not dm_target:
                    error = f'No user found with username "{other_user}".'
                elif dm_target == user:
                    error = "You can't DM yourself."
                elif not _get_workspace_role(dm_target, workspace):
                    error = f'{other_user} is not a member of this workspace.'

            if not error:
                # auto-generate a stable name and reuse existing DM if present
                pair = sorted([user.username, dm_target.username])
                name = f'dm-{pair[0]}-{pair[1]}'
                existing = Channel.objects.filter(
                    workspace=workspace, channel_type='direct', name=name
                ).first()
                if existing:
                    return redirect('channel', channel_id=existing.channel_id)
        else:
            name = request.POST.get('name', '').strip().lower()
            if not name:
                error = 'Channel name is required.'
            elif channel_type not in ('public', 'private'):
                error = 'Invalid channel type.'
            elif Channel.objects.filter(name=name, workspace=workspace).exists():
                error = f'A channel named #{name} already exists in this workspace.'

        if error:
            return render(request, 'core/channel_new.html',
                          {'workspace': workspace, 'error': error})

        with transaction.atomic():
            channel = Channel.objects.create(
                name=name,
                workspace=workspace,
                channel_type=channel_type,
                created_by=user,
            )
            ChannelMembership.objects.create(channel=channel, user=user)
            if dm_target:
                ChannelMembership.objects.create(channel=channel, user=dm_target)

        return redirect('channel', channel_id=channel.channel_id)

    return render(request, 'core/channel_new.html', {'workspace': workspace})


@login_required
def channel(request, channel_id):
    user    = get_current_user(request)
    channel = get_object_or_404(Channel, pk=channel_id)

    if not _get_workspace_role(user, channel.workspace):
        return render(request, 'core/403.html', status=403)

    is_member = _is_channel_member(user, channel)

    if channel.channel_type != 'public' and not is_member:
        return render(request, 'core/403.html', status=403)

    if request.method == 'POST':
        return render(request, 'core/403.html', status=403)

    members = (
        ChannelMembership.objects
        .filter(channel=channel)
        .select_related('user')
        .order_by('user__username')
    )

    return render(request, 'core/channel.html', {
        'user':      user,
        'channel':   channel,
        'members':   members,
        'is_member': is_member,
        'emojis':    EMOJI_SET,
    })


@login_required
@require_POST
def channel_join(request, channel_id):
    user    = get_current_user(request)
    channel = get_object_or_404(Channel, pk=channel_id, channel_type='public')

    if not _get_workspace_role(user, channel.workspace):
        return render(request, 'core/403.html', status=403)

    ChannelMembership.objects.get_or_create(channel=channel, user=user)
    return redirect('channel', channel_id=channel_id)


@login_required
def channel_invite(request, channel_id):
    user    = get_current_user(request)
    channel = get_object_or_404(Channel, pk=channel_id, channel_type='private')

    if channel.created_by != user:
        return render(request, 'core/403.html', status=403)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        error    = None
        invitee  = User.objects.filter(username=username).first()

        if not username:
            error = 'Username is required.'
        elif not invitee:
            error = f'No user found with username "{username}".'
        elif not _get_workspace_role(invitee, channel.workspace):
            error = f'{username} is not a member of this workspace.'
        elif _is_channel_member(invitee, channel):
            error = f'{username} is already in this channel.'
        elif ChannelInvitation.objects.filter(channel=channel, invitee_user=invitee, accepted=False).exists():
            error = f'A pending invitation for {username} already exists.'

        if error:
            return render(request, 'core/channel_invite.html',
                          {'channel': channel, 'error': error})

        ChannelInvitation.objects.create(
            channel=channel, invited_by=user, invitee_user=invitee
        )
        return render(request, 'core/channel_invite.html',
                      {'channel': channel, 'success': f'Invitation sent to {username}.'})

    return render(request, 'core/channel_invite.html', {'channel': channel})


@login_required
def channel_invitation_accept(request, invitation_id):
    user       = get_current_user(request)
    invitation = get_object_or_404(ChannelInvitation, pk=invitation_id, invitee_user=user, accepted=False)

    with transaction.atomic():
        ChannelMembership.objects.get_or_create(channel=invitation.channel, user=user)
        invitation.accepted    = True
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted', 'accepted_at'])

    return redirect('channel', channel_id=invitation.channel.channel_id)


@login_required
def channel_invitation_decline(request, invitation_id):
    user       = get_current_user(request)
    invitation = get_object_or_404(ChannelInvitation, pk=invitation_id, invitee_user=user, accepted=False)
    invitation.delete()
    return redirect('channel_list', workspace_id=invitation.channel.workspace_id)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@login_required
def search(request):
    user  = get_current_user(request)
    query = request.GET.get('q', '').strip()

    results = []
    if query:
        member_channel_ids   = ChannelMembership.objects.filter(user=user).values_list('channel_id', flat=True)
        member_workspace_ids = WorkspaceMembership.objects.filter(user=user).values_list('workspace_id', flat=True)

        results = (
            Message.objects
            .filter(
                body__icontains=query,
                channel_id__in=member_channel_ids,
                channel__workspace_id__in=member_workspace_ids,
            )
            .select_related('channel', 'channel__workspace', 'posted_by')
            .order_by('posted_at')
        )

    return render(request, 'core/search.html', {
        'user':    user,
        'query':   query,
        'results': results,
    })


# ---------------------------------------------------------------------------
# AJAX endpoints — messages & reactions
# ---------------------------------------------------------------------------

def _messages_to_json(messages, user):
    """Shared helper: serialise a queryset of messages with reaction data."""
    msg_ids = [m.message_id for m in messages]
    if not msg_ids:
        return []

    # Reaction counts per message per emoji
    reaction_rows = (
        MessageReaction.objects
        .filter(message_id__in=msg_ids)
        .values('message_id', 'emoji')
        .annotate(count=Count('id'))
    )
    counts = {}
    for r in reaction_rows:
        counts.setdefault(r['message_id'], {})[r['emoji']] = r['count']

    # Which emojis the current user has used
    my = set(
        MessageReaction.objects
        .filter(message_id__in=msg_ids, user=user)
        .values_list('message_id', 'emoji')
    )

    return [
        {
            'id':          m.message_id,
            'body':        m.body,
            'nickname':    m.posted_by.nickname,
            'username':    m.posted_by.username,
            'posted_at':   m.posted_at.strftime('%-d %b %H:%M'),
            'reactions':   counts.get(m.message_id, {}),
            'my_reactions': [e for (mid, e) in my if mid == m.message_id],
        }
        for m in messages
    ]


@login_required
def channel_messages_json(request, channel_id):
    user    = get_current_user(request)
    channel = get_object_or_404(Channel, pk=channel_id)

    if not _get_workspace_role(user, channel.workspace):
        return JsonResponse({'error': 'forbidden'}, status=403)
    if channel.channel_type != 'public' and not _is_channel_member(user, channel):
        return JsonResponse({'error': 'forbidden'}, status=403)

    qs = Message.objects.filter(channel=channel).select_related('posted_by').order_by('posted_at')
    after = request.GET.get('after')
    if after:
        qs = qs.filter(message_id__gt=after)

    return JsonResponse(_messages_to_json(qs, user), safe=False)


@login_required
@require_POST
def message_post(request, channel_id):
    user    = get_current_user(request)
    channel = get_object_or_404(Channel, pk=channel_id)

    if not _get_workspace_role(user, channel.workspace):
        return JsonResponse({'error': 'forbidden'}, status=403)
    if not _is_channel_member(user, channel):
        return JsonResponse({'error': 'forbidden'}, status=403)

    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'empty'}, status=400)

    msg = Message.objects.create(channel=channel, posted_by=user, body=body)
    return JsonResponse(_messages_to_json([msg], user)[0])


@login_required
@require_POST
def message_react(request, message_id):
    user    = get_current_user(request)
    message = get_object_or_404(Message, pk=message_id)
    emoji   = request.POST.get('emoji', '')

    if emoji not in EMOJI_SET:
        return JsonResponse({'error': 'invalid emoji'}, status=400)

    if not _get_workspace_role(user, message.channel.workspace):
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        MessageReaction.objects.create(message=message, user=user, emoji=emoji)
        reacted = True
    except IntegrityError:
        MessageReaction.objects.filter(message=message, user=user, emoji=emoji).delete()
        reacted = False

    counts = {}
    for r in (MessageReaction.objects.filter(message=message)
              .values('emoji').annotate(count=Count('id'))):
        counts[r['emoji']] = r['count']

    return JsonResponse({'reacted': reacted, 'counts': counts})
