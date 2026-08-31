"""users — 커스텀 User (email 로그인, PM/EMPLOYEE, 재직상태)."""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """email을 로그인 식별자로 쓰는 커스텀 매니저."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("email은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.Role.PM)
        extra.setdefault("must_change_password", False)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("superuser는 is_staff=True, is_superuser=True 여야 합니다.")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        PM = "PM", "PM"
        EMPLOYEE = "EMPLOYEE", "직원"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "활성"
        LEAVE = "LEAVE", "휴직"
        RESIGNED = "RESIGNED", "퇴사"
        LOCKED = "LOCKED", "잠금"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYEE)
    must_change_password = models.BooleanField(default=True)

    employee_no = models.CharField(max_length=64, unique=True, null=True, blank=True)
    department = models.CharField(max_length=64, null=True, blank=True)
    position = models.CharField(max_length=64, null=True, blank=True)
    job_title = models.CharField(max_length=64, null=True, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    hire_date = models.DateField(null=True, blank=True)
    resign_date = models.DateField(null=True, blank=True)

    slack_email = models.EmailField(null=True, blank=True)
    github_email = models.EmailField(null=True, blank=True)
    tech_stack = models.TextField(null=True, blank=True)
    certifications = models.TextField(null=True, blank=True)
    past_projects = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_pm(self) -> bool:
        return self.role == self.Role.PM
