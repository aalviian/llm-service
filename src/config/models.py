from django.db import models


class JuloCustomer(models.Model):
    customer_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "julodb"
        db_table = "customers"
        managed = False

    def __str__(self):
        return f"{self.name} ({self.customer_id})"


def get_julo_customers():
    """Example function to query JuloDB"""
    return JuloCustomer.objects.using("julodb").all()


def create_julo_customer(customer_data):
    """Example function to create customer in JuloDB"""
    customer = JuloCustomer(**customer_data)
    customer.save(using="julodb")
    return customer


class JuloUser(models.Model):
    """JuloDB User model for authentication"""

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "julodb"
        db_table = "auth_user"
        managed = False

    def __str__(self):
        return self.username

    def check_password(self, raw_password):
        """Check password against stored hash"""
        from django.contrib.auth.hashers import check_password

        return check_password(raw_password, self.password)


def authenticate_julo_user(username, password):
    """Authenticate user against JuloDB"""
    try:
        user = JuloUser.objects.using("julodb").get(username=username, is_active=True)
        if user.check_password(password):
            return user
    except JuloUser.DoesNotExist:
        pass
    return None
