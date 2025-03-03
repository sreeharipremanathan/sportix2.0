from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from datetime import timedelta
import uuid

# Create your models here.
class Category(models.Model):
    category= models.TextField()

class Products(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    description = models.TextField()
    image = models.ImageField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.offer_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Packed", "Packed"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField()
    mobile_number = models.CharField(max_length=15, null=True, blank=True)  # Allow null values
    pincode = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)  # Razorpay Payment ID
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="Pending")  # Payment status
    payment_method = models.CharField(max_length=20, choices=[("COD", "Cash on Delivery"), ("Online", "Online Payment")])
    def is_cancellable(self):
        return (now() - self.created_at) <= timedelta(days=2) and self.status == "Pending"
    def __str__(self):
        return f"Order {self.id} - {self.user.username}"

class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)







# class Product(models.Model):
#     name = models.CharField(max_length=200)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE)
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     stock = models.PositiveIntegerField()
#     description = models.TextField()
#     image = models.ImageField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name