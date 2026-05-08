from django.db import models
from django.db.models import CompositePrimaryKey


class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=100, unique=True)
    nickname = models.CharField(max_length=100)
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.username


class Workspace(models.Model):
    workspace_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'workspace'

    def __str__(self):
        return self.name


class WorkspaceMembership(models.Model):
    pk = CompositePrimaryKey('workspace_id', 'user_id')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, db_column='workspace_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    role = models.CharField(max_length=10, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'workspace_membership'


class WorkspaceInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, db_column='workspace_id')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='invited_by', related_name='sent_workspace_invitations')
    invitee_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='invitee_user_id', related_name='received_workspace_invitations')
    invitee_email = models.EmailField(max_length=255)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'workspace_invitation'


class Channel(models.Model):
    channel_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, db_column='workspace_id')
    channel_type = models.CharField(max_length=10)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'channel'
        unique_together = [('name', 'workspace')]

    def __str__(self):
        return f'#{self.name}'


class ChannelMembership(models.Model):
    pk = CompositePrimaryKey('channel_id', 'user_id')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, db_column='channel_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'channel_membership'


class ChannelInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, db_column='channel_id')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='invited_by', related_name='sent_channel_invitations')
    invitee_user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='invitee_user_id', related_name='received_channel_invitations')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'channel_invitation'


class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    body = models.TextField()
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, db_column='channel_id')
    posted_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='posted_by')
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'message'
        ordering = ['posted_at']


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, db_column='message_id', related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'message_reaction'
