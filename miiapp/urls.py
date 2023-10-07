from django.urls import path

from miiapp import views

urlpatterns = [
    path("", views.index, name="index"),
    path("signin", views.signin, name="signin"),
    path("signup", views.signup, name="signup"),
    path("privacy", views.privacy, name="privacy"),
    path("archive", views.archive, name="archive"),
    path("logout", views.disconnect, name="disconnect"),
    path("nnid/<str:nnid>", views.viewNNID, name="viewnnid"),
    path("random", views.randomNNID, name="randomnnid"),
    path("search", views.search, name="search"),
    path("owned", views.owned, name="owned"),
    path("api", views.api, name="api"),
    path("api/nnidinfo", views.getNNIDInfo, name="nnidinfo"),
    path("api/gethash", views.getHash, name="gethash"),
    path("mii/<str:hash>/<str:type>", views.miiImage, name="miiimage"),
    path("complaint/<str:nnid>", views.complaint, name="complaint"),
    path("miniadmin", views.miniadmin, name="miniadmin"),
    path("complaints", views.complaints, name="complaints"),
    path("delete", views.delete, name="delete"),
    path("refresh/<str:nnid>", views.refresh, name="refresh"),
    path("favorite/<str:nnid>", views.favorite, name="favorite"),
    path("favorites", views.favorites, name="favorites"),
    path("qna", views.qna, name="qna")
]