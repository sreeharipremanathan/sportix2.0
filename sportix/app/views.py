from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate,login,logout
from .models import *
import os
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import razorpay
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



# Create your views here.
def sportix_login(req):
    if 'admin' in req.session:
        return redirect(reverse(admin_home))  # Use the correct URL name
    else:
        if req.method == 'POST':
            uname = req.POST['uname']
            password = req.POST['password']
            data = authenticate(username=uname, password=password)
            if data:
                login(req, data)
                if data.is_superuser:
                    req.session['admin'] = uname
                    return redirect(reverse('admin_home'))  # Fix this
                else:
                    req.session['user'] = uname
                    return redirect(reverse('sportix_home'))  # Fix this
            else:
                messages.warning(req, 'Invalid username or password')
                return redirect(reverse('sportix_login'))
    return render(req, 'login.html')

def register(req):
    if req.method == 'POST':
        name = req.POST['name']
        email = req.POST['email']
        password = req.POST['password']
        
        try:
            validate_password(password)
            
            
            if User.objects.filter(email=email).exists():
                messages.warning(req, 'User with this email already exists.')
                return redirect(register)

            
            user = User.objects.create_user(first_name=name, username=email, email=email, password=password)
            user.save()

            
            send_mail(
                'Account Registration',
                'Your Sportix account registration was successful.',
                settings.EMAIL_HOST_USER,
                [email]
            )

            messages.success(req, 'Registration successful. Please log in.')
            return redirect(sportix_login)

        except ValidationError as e:
            messages.error(req, ', '.join(e)) 
            return redirect(register)
        
    return render(req, 'register.html')

def sportix_logout(req):
    logout(req)
    req.session.flush()
    return redirect(sportix_login)

# -------admin---------------
def admin_home(req):
    if 'admin' in req.session:
        products = Products.objects.all()
        return render(req, 'admin/admin_home.html', {'products': products})
    else:
        return render(sportix_login)

def add_category(req):
    if 'admin' in req.session:
        if req.method == 'POST':
            category=req.POST['category']
            data=Category.objects.create(category=category)
            data.save()
            return redirect(add_category)
        else:
            data=Category.objects.all()
            return render(req,'admin/add_category.html',{'data':data})
    else:
         return redirect(admin_home)

def add_product(req):
    if 'admin' in req.session:
        if req.method == 'POST':
            name = req.POST['name']
            category_id = req.POST['category']  # Get category ID instead of name
            price = req.POST['price']
            offer_price = req.POST['offer_price']
            stock = req.POST['stock']
            description = req.POST['description']
            file = req.FILES['image']

            try:
                category = Category.objects.get(id=category_id)  # Fetch by ID
            except Category.DoesNotExist:
                messages.error(req, "Selected category does not exist.")
                return redirect('add_product')

            # Create product entry
            data = Products.objects.create(
                name=name,
                category=category,
                price=price,
                offer_price=offer_price,
                stock=stock,
                description=description,
                image=file
            )
            data.save()
            messages.success(req, 'Product added successfully!')
            return redirect(add_product)

        else:
            data = Category.objects.all()
            return render(req, 'admin/add_product.html', {'data': data})

    return redirect('sportix_login')

def edit_product(req, product_id):
    if 'admin' in req.session:
        product = get_object_or_404(Products, id=product_id)

        if req.method == 'POST':
            name = req.POST['name']
            category_id = req.POST['category']
            price = req.POST['price']
            offer_price = req.POST['offer_price']
            stock = req.POST['stock']
            description = req.POST['description']

            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                messages.error(req, "Selected category does not exist.")
                return redirect('edit_product', product_id=product.id)

            product.name = name
            product.category = category
            product.price = price
            product.offer_price = offer_price
            product.stock = stock
            product.description = description

            # Update image only if a new file is uploaded
            if 'image' in req.FILES:
                product.image = req.FILES['image']

            product.save()
            messages.success(req, 'Product updated successfully!')
            return redirect(admin_home)

        categories = Category.objects.all()
        return render(req, 'admin/edit_product.html', {'product': product, 'categories': categories})

    return redirect(edit_product)

def delete_pro(req,id):
    data=Products.objects.get(pk=id)
    url=data.image.url
    url=url.split('/')[-1]
    os.remove('media/'+url)
    data.delete()
    return redirect(admin_home)

def delete_category(req,id):
    data=Category.objects.get(pk=id)
    data.delete()
    return redirect(add_category)

def admin_orders(request):
    orders = Order.objects.all().order_by("-created_at")  # Show latest orders first
    return render(request, "admin/admin_orders.html", {"orders": orders})

def update_order_status(request, order_id, status):
    order = get_object_or_404(Order, id=order_id)
    order.status = status
    order.save()

    # Email only if status is packed, shipped, or delivered
    if status in ["Packed", "Shipped", "Delivered"]:
        subject = f"Your Order #{order.id} is {status}!"
        message = f"Hello {order.user.username},\n\nYour order (ID: {order.id}) has been {status}.\n\nThank you for shopping with us!"
        recipient_email = order.user.email  # Assuming order has a user field

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  # Sender email
            [recipient_email],  # Receiver email
            fail_silently=False,
        )

    return redirect(admin_orders)

# --------user---------------
def sportix_home(req):
    if 'admin' in req.session:
        return redirect(admin_home)
    else:
        data=Products.objects.all()
        cat=Category.objects.all()
        return render(req,'user/user_home.html',{'data':data,'cat':cat})
    
def view_category(req,id):
    category = Category.objects.get(pk=id)
    cat=Category.objects.all()
    product = Products.objects.filter(category=category)
    return render(req, 'user/category.html', {'category': category,'product': product,"cat":cat}) 

def search_products(request):
    query = request.GET.get('q', '')  
    results = Products.objects.filter(name__icontains=query)
    cat=Category.objects.all()
    return render(request, 'user/search_results.html', {'query': query, 'results': results,"cat":cat})

def view_product(request, id):
    cat=Category.objects.all()
    product = get_object_or_404(Products, id=id)
    related_products = Products.objects.filter(category=product.category).exclude(id=product.id)[:4]  # Show related products
    return render(request, 'user/view_product.html', {'product': product, 'related_products': related_products,"cat":cat})

def add_to_cart(request, product_id):
    product = Products.objects.get(id=product_id)
    cart = request.session.get("cart", {})

    if str(product_id) not in cart:
        cart[str(product_id)] = {
            "name": product.name,
            "price": float(product.offer_price),  
            "quantity": int(request.POST.get("quantity", 1)),
            "image": product.image.url if product.image else "",
        }

    cart[str(product_id)]["subtotal"] = cart[str(product_id)]["quantity"] * cart[str(product_id)]["price"]

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("view_cart")

def view_cart(request):
    cat=Category.objects.all()
    cart = request.session.get("cart", {})
    total_price = sum(item["price"] * item["quantity"] for item in cart.values())
    return render(request, "user/cart.html", {"cart": cart, "total_price": total_price,'cat':cat})

def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})

    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session["cart"] = cart
        request.session.modified = True

    return redirect(view_cart)

def update_cart(request, product_id, action):
    cart = request.session.get("cart", {})

    if str(product_id) in cart:
        if action == "increase":
            cart[str(product_id)]["quantity"] += 1
        elif action == "decrease":
            if cart[str(product_id)]["quantity"] > 1:
                cart[str(product_id)]["quantity"] -= 1
            else:
                del cart[str(product_id)]
                request.session["cart"] = cart
                request.session.modified = True
                return redirect("view_cart")  

        
        cart[str(product_id)]["subtotal"] = cart[str(product_id)]["quantity"] * cart[str(product_id)]["price"]

        request.session["cart"] = cart
        request.session.modified = True

    return redirect("view_cart")

def contact_us(request):
    cat=Category.objects.all()
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        full_message = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        send_mail(
            f"Contact Us - {subject}",
            full_message,
            email, 
            ["sportixmerch@gmail.com"], 
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully!")
        return redirect(contact_us)

    return render(request, "user/contact.html",{'cat':cat})




def checkout(request):
    user = request.user
    cart = request.session.get("cart", {}).copy()  # Copy to avoid modifying original
    buy_now = request.session.get("buy_now", None)

    if "buy_now" in request.session and cart:  # If cart exists, remove buy_now
        request.session.pop("buy_now", None)
    elif "cart" in request.session and buy_now:  # If buy_now exists, remove cart
        request.session.pop("cart", None)

    saved_addresses = request.session.get("saved_addresses", [])

    if request.method == "POST":
        selected_address = request.POST.get("selected_address")
        new_address = request.POST.get("new_address")

        address = new_address if new_address else selected_address
        if not address:
            messages.error(request, "Please enter or select an address.")
            return redirect("checkout")

        if new_address and new_address not in saved_addresses:
            saved_addresses.append(new_address)
            request.session["saved_addresses"] = saved_addresses

        request.session["checkout_address"] = address
        request.session.modified = True
        return redirect(complete_order)

    # 👇 Now we are 100% sure only one of them will exist
    if buy_now:
        products = [buy_now]
        total_price = float(buy_now["price"])
    else:
        products = cart.values()
        total_price = sum(float(item["price"]) * item["quantity"] for item in cart.values())

    expected_delivery = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")

    context = {
        "products": products,
        "total_price": total_price,
        "expected_delivery": expected_delivery,
        "saved_addresses": saved_addresses,
    }

    return render(request, "user/checkout.html", context)


def complete_order(request):
    address = request.session.get("checkout_address")
    
    if not address:
        return redirect(checkout)

    buy_now = request.session.pop("buy_now", None)  # Remove buy_now after order
    cart = request.session.get("cart", {}).copy()  # Copy cart to prevent clearing on errors

    if buy_now:
        Order.objects.create(
            user=request.user,
            product_id=buy_now["id"],
            quantity=1,
            total_price=buy_now["price"],
            address=address,
        )
    elif cart:
        for product_id, item in cart.items():
            Order.objects.create(
                user=request.user,
                product_id=product_id,
                quantity=item["quantity"],
                total_price=item["quantity"] * item["price"],
                address=address,
            )
        request.session.pop("cart", None)  # 🚀 Only clear cart when order is placed!

    request.session.pop("checkout_address", None)
    request.session.modified = True

    return redirect(order_success)


def order_success(request):
    return render(request, "user/order_success.html")

# def buy_now(request,id):
#     product = Products.objects.get(id=id)

#     request.session["buy_now"] = {
#         "id": product.id,
#         "name": product.name,
#         "price": float(product.offer_price),
#         "quantity": 1,  
#     }
#     request.session.modified = True

#     return redirect(checkout) 

def buy_now(request, id):
    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))  # Get quantity from the form
    else:
        quantity = 1  # Default to 1 if not a POST request

    product = Products.objects.get(id=id)
    total_price = float(product.offer_price) * quantity

    request.session["buy_now"] = {
        "id": product.id,
        "name": product.name,
        "price": total_price,
        "quantity": quantity,  
    }
    request.session.modified = True

    return redirect(checkout)

def user_profile(req):
    cat=Category.objects.all()
    
    user = req.user  
    orders = Order.objects.filter(user=user).order_by('-created_at')

    context = {
        "orders": orders,"cat":cat
    }

    return render(req, "user/user_profile.html", context)


def update_username(request):
    if request.method == "POST":
        new_first_name = request.POST.get("name")
        new_username = request.POST.get("username")

        
        if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
            messages.error(request, "This username is already taken. Please choose another one.")
            return redirect(user_profile) 

        
        if new_first_name and new_username:
            request.user.first_name = new_first_name
            request.user.username = new_username
            request.user.save()
            messages.success(request, "Username updated successfully!")
        else:
            messages.error(request, "Username and Name cannot be empty.")

    return redirect(user_profile)

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.is_cancellable():
        order.delete()
        messages.success(request, "Your order has been cancelled and removed.")
    else:
        messages.error(request, "You can only cancel orders within 2 days.")

    return redirect(user_profile)