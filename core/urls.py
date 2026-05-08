from django.urls import path
from core import views

urlpatterns = [
    # Auth
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),

    # Workspaces
    path('workspaces/new/', views.workspace_new, name='workspace_new'),
    path('workspaces/<int:workspace_id>/', views.workspace, name='workspace'),
    path('workspaces/<int:workspace_id>/invite/', views.workspace_invite, name='workspace_invite'),
    path('workspaces/<int:workspace_id>/members/<int:user_id>/remove/', views.member_remove, name='member_remove'),
    path('workspaces/<int:workspace_id>/members/<int:user_id>/promote/', views.member_promote, name='member_promote'),

    # Workspace invitations
    path('invitations/', views.invitations, name='invitations'),
    path('invitations/<int:invitation_id>/accept/', views.invitation_accept, name='invitation_accept'),
    path('invitations/<int:invitation_id>/decline/', views.invitation_decline, name='invitation_decline'),

    # Channels
    path('workspaces/<int:workspace_id>/channels/', views.channel_list, name='channel_list'),
    path('workspaces/<int:workspace_id>/channels/new/', views.channel_new, name='channel_new'),
    path('workspaces/<int:workspace_id>/members/search/', views.workspace_members_search, name='workspace_members_search'),
    path('channels/<int:channel_id>/', views.channel, name='channel'),
    path('channels/<int:channel_id>/join/', views.channel_join, name='channel_join'),
    path('channels/<int:channel_id>/invite/', views.channel_invite, name='channel_invite'),

    # Channel invitations
    path('channel-invitations/<int:invitation_id>/accept/', views.channel_invitation_accept, name='channel_invitation_accept'),
    path('channel-invitations/<int:invitation_id>/decline/', views.channel_invitation_decline, name='channel_invitation_decline'),

    # Search
    path('search/', views.search, name='search'),

    # AJAX
    path('channels/<int:channel_id>/messages/json/', views.channel_messages_json, name='channel_messages_json'),
    path('channels/<int:channel_id>/post/', views.message_post, name='message_post'),
    path('messages/<int:message_id>/react/', views.message_react, name='message_react'),
]
