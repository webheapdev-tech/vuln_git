from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register", views.register, name="register"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("search", views.search_users, name="search"),
    path("docs/<int:doc_id>", views.document_detail, name="doc_detail"),
    path("transfer", views.transfer, name="transfer"),
    path("comments", views.comments, name="comments"),
    path("diag", views.diagnostics, name="diag"),
    path("read-log", views.read_log, name="read_log"),
    path("fetch", views.fetch_url, name="fetch"),
    path("deserialize", views.deserialize_debug, name="deserialize"),
    path("token-login", views.token_login, name="token_login"),
    path("eval", views.eval_console, name="eval_console"),
    path("zip-import", views.zip_import, name="zip_import"),
    path("save-note", views.save_note, name="save_note"),
    path("go", views.open_redirect, name="go"),
    path("profile/update", views.update_profile, name="profile_update"),
    path("internal/dump", views.internal_dump, name="internal_dump"),
]
