from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.files.storage import default_storage

class Job(models.Model):
    user = models.ForeignKey('backend.User', on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    industries = models.CharField(max_length=255)
    locations = models.CharField(max_length=255)
    task_id = models.CharField(max_length=255, null=True, blank=True)
    
    initial_csv_file = models.FileField(upload_to='initial_files/', null=True, blank=True)
    final_csv_file = models.FileField(upload_to='postprocessed_files/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job {self.id} for {self.user}"

@receiver(post_delete, sender=Job)
def delete_job_files(sender, instance, **kwargs):
    if instance.initial_csv_file and default_storage.exists(instance.initial_csv_file.name):
        instance.initial_csv_file.delete(save=False)
    if instance.final_csv_file and default_storage.exists(instance.final_csv_file.name):
        instance.final_csv_file.delete(save=False)

class UserPayment(models.Model):
    user = models.OneToOneField('backend.User', on_delete=models.CASCADE)
    payment_bool = models.BooleanField(default=False)
    stripe_checkout_id = models.CharField(max_length=500)
    subscription_plan = models.CharField(max_length=255, null=True, blank=True)
    max_jobs_allowed = models.IntegerField(default=0)
    jobs_submitted = models.IntegerField(default=0)

    def __str__(self):
        return f"Payment status for {self.user.email}: {'Paid' if self.payment_bool else 'Not Paid'}"

@receiver(post_save, sender='backend.User')
def create_user_payment(sender, instance, created, **kwargs):
    if created:
        UserPayment.objects.create(user=instance)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email, password)
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    email = models.EmailField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_admin

class OneTimePayment(models.Model):
    user = models.ForeignKey('backend.User', on_delete=models.CASCADE)
    job = models.ForeignKey('backend.Job', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
