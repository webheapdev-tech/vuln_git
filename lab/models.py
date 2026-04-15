from django.db import models


class LabUser(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password_plain = models.CharField(max_length=128)
    email = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=20, default="user")
    balance = models.IntegerField(default=1000)

    def __str__(self):
        return self.username


class SecretDocument(models.Model):
    owner = models.ForeignKey(LabUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_private = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class PublicComment(models.Model):
    author = models.CharField(max_length=60)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ApiCredential(models.Model):
    user = models.ForeignKey(LabUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=120, unique=True)
    active = models.BooleanField(default=True)
