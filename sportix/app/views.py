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
import json


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
                messages.error(req, 'Invalid username or password')
                return redirect(reverse('sportix_login'))
    return render(req, 'login.html')

def send_verification_email(user):
    token, created = EmailVerification.objects.get_or_create(user=user)
    verification_link = f"http://127.0.0.1:8000/verify-email/{token.token}/"

    send_mail(
        "Verify Your Email",
        f"Click the link to verify your email: {verification_link}",
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

def register(req):
    if req.method == 'POST':
        name = req.POST['name']
        email = req.POST['email']
        password = req.POST['password']

        try:
            validate_password(password)
            
            if User.objects.filter(username=email).exists():
                messages.warning(req, 'This email is already registered. Try logging in.')
                return redirect(register)

            # 🔥 **Check if an unverified user exists, delete and re-register**
            existing_user = User.objects.filter(email=email, is_active=False).first()
            if existing_user:
                existing_user.delete()  

            
            user = User.objects.create_user(
                first_name=name, username=email, email=email, password=password, is_active=False
            )
            user.save()

            send_verification_email(user)  # 🔥 Send verification email
            
            messages.success(req, 'Registration successful. Please check your email to verify your account.')
            return redirect('check_email')  

        except ValidationError as e:
            messages.error(req, ', '.join(e)) 
            return redirect(register)
        
    return render(req, 'register.html')

def check_email(request):
    return render(request, 'check_email.html')

def verify_email(request, token):
    try:
        verification = EmailVerification.objects.get(token=token)
        user = verification.user
        user.is_active = True 
        user.save()
        verification.delete()  
        messages.success(request, "Your email has been verified! You can now log in.")
        return redirect('sportix_login')  
    except EmailVerification.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
        return redirect('register')

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
    product = get_object_or_404(Products, id=product_id)
    cart = request.session.get("cart", {})

    quantity = int(request.POST.get("quantity", 1))  # Get selected quantity
    if quantity > product.stock:
        messages.error(request, f"Only {product.stock} items available in stock.")
        return redirect("view_product", product_id=product_id)  # Redirect back

    if str(product_id) in cart:
        if cart[str(product_id)]["quantity"] + quantity > product.stock:
            messages.error(request, f"Only {product.stock} items available in stock.")
            return redirect("cart")  # Redirect back to cart

        cart[str(product_id)]["quantity"] += quantity
    else:
        cart[str(product_id)] = {
            "name": product.name,
            "price": float(product.offer_price),  
            "quantity": int(request.POST.get("quantity", 1)),
            "image": product.image.url if product.image else "",
        }
    cart[str(product_id)]["subtotal"] = cart[str(product_id)]["quantity"] * cart[str(product_id)]["price"]
    request.session["cart"] = cart
    request.session.modified = True
    messages.success(request, f"{product.name} added to cart.")
    return redirect("view_cart") 

# def add_to_cart(request, product_id):
#     product = Products.objects.get(id=product_id)
#     cart = request.session.get("cart", {})

#     if str(product_id) not in cart:
#         cart[str(product_id)] = {
#             "name": product.name,
#             "price": float(product.offer_price),  
#             "quantity": int(request.POST.get("quantity", 1)),
#             "image": product.image.url if product.image else "",
#         }

#     cart[str(product_id)]["subtotal"] = cart[str(product_id)]["quantity"] * cart[str(product_id)]["price"]

#     request.session["cart"] = cart
#     request.session.modified = True

#     return redirect("view_cart")

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
        product = get_object_or_404(Products, id=product_id)  # Get product from DB
        current_quantity = cart[str(product_id)]["quantity"]

        if action == "increase":
            if current_quantity < product.stock:  # Check stock before increasing
                cart[str(product_id)]["quantity"] += 1
            else:
                messages.error(request, f"Only {product.stock} units available.")
        
        elif action == "decrease":
            if current_quantity > 1:
                cart[str(product_id)]["quantity"] -= 1
            else:
                del cart[str(product_id)]  # Remove from cart if quantity reaches 0
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



# working good
# def checkout(request):
#     user = request.user
#     cart = request.session.get("cart", {}).copy()  # Copy cart session to avoid unwanted clearing
#     buy_now = request.session.get("buy_now", None)

#     # Don't remove "buy_now" or "cart" in checkout, handle them separately in complete_order

#     saved_addresses = request.session.get("saved_addresses", []) 

#     if request.method == "POST":
#         selected_address = request.POST.get("selected_address")
#         new_address = request.POST.get("new_address")

#         # Choose address (prioritizing new_address if provided)
#         address = new_address if new_address else selected_address
#         if not address:
#             messages.error(request, "Please enter or select an address.")
#             return redirect("checkout")

#         if new_address and new_address not in saved_addresses:
#             saved_addresses.append(new_address)
#             request.session["saved_addresses"] = saved_addresses

#         request.session["checkout_address"] = address  
#         request.session.modified = True
#         return redirect(complete_order) 

#     # Handling "Buy Now" separately without clearing the cart
#     if buy_now:
#         products = [buy_now]
#         total_price = float(buy_now["price"])
#     else:
#         products = cart.values()
#         total_price = sum(float(item["price"]) * item["quantity"] for item in cart.values())

#     expected_delivery = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")

#     context = {
#         "products": products,
#         "total_price": total_price,
#         "expected_delivery": expected_delivery,
#         "saved_addresses": saved_addresses,
#     }
#     print("SESSION DATA:", request.session.get("buy_now"))
#     return render(request, "user/checkout.html", context)


def checkout(request):
    print(request.method)
    user = request.user
    cart = request.session.get("cart", {}).copy()
    buy_now = request.session.get("buy_now", None)
    saved_addresses = request.session.get("saved_addresses", [])
    # Ensure saved_addresses is a list of dictionaries
    if isinstance(saved_addresses, str):  
        try:
            saved_addresses = json.loads(saved_addresses)  # Convert JSON string to list
        except json.JSONDecodeError:
            saved_addresses = []  # Reset if invalid

    # Ensure it's a valid list of dictionaries
    if not isinstance(saved_addresses, list) or any(not isinstance(addr, dict) for addr in saved_addresses):
        saved_addresses = []

    # Fix session conflicts
    if "buy_now" in request.session and cart:
        del request.session["buy_now"]
    elif "cart" in request.session and buy_now:
        del request.session["cart"]

    if request.method == "POST":
        selected_address = request.POST.get("selected_address")
        new_address = request.POST.get("new_address")
        mobile_number = request.POST.get("mobile_number")
        pincode = request.POST.get("pincode")

        address = new_address if new_address else selected_address

        if not address or not mobile_number or not pincode:
            messages.error(request, "Please enter all required details.")
            return redirect("checkout")

        if new_address and not any(addr["address"] == new_address for addr in saved_addresses):
            saved_addresses.append({"address": new_address, "mobile": mobile_number, "pincode": pincode})
            request.session["saved_addresses"] = json.dumps(saved_addresses)  # Store as JSON string


        request.session["checkout_details"] = {
            "address": address,
            "mobile": mobile_number,
            "pincode": pincode,
        }
        request.session.modified = True 

        return redirect(complete_order) 
    
    # Determine total price
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
        "razorpay_key": settings.RAZORPAY_KEY_ID, 
    }

    return render(request, "user/checkout.html", context)



@csrf_exempt
def verify_payment_and_complete_order(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        address = request.session.get("checkout_address")
        buy_now = request.session.get("buy_now", None)
        cart = request.session.get("cart", {})

        if not address:
            return redirect("checkout")

        # Verify Razorpay Payment
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            return redirect("payment_failed")

        # Create Order in Database
        if buy_now:
            Order.objects.create(
                user=request.user,
                product_id=buy_now["id"],
                quantity=buy_now["quantity"],
                total_price=buy_now["price"],
                address=address,
            )
        elif cart:
            for product_id, item in cart.items():
                Order.objects.create(
                    user=request.user,
                    product_id=product_id,
                    quantity=item["quantity"],
                    total_price=item["price"] * item["quantity"],
                    address=address,
                )

        # Clear Session after Order is Placed
        request.session.pop("checkout_address", None)
        request.session.pop("buy_now", None)
        request.session.pop("cart", None)
        request.session.modified = True

        return redirect("payment_success")


@csrf_exempt
def complete_razor_order(request):
    if request.method == "POST":
        data = json.loads(request.body)
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")


# @csrf_exempt
# def complete_order(request):
#     if request.method == "POST":
#         razorpay_payment_id = request.POST.get("razorpay_payment_id")
#         razorpay_order_id = request.POST.get("razorpay_order_id")
#         razorpay_signature = request.POST.get("razorpay_signature")

#         address = request.session.get("checkout_address")
#         buy_now = request.session.get("buy_now", None)
#         cart = request.session.get("cart", {})

#         if not address:
#             return redirect("checkout")

#         # Verify Razorpay Payment
#         client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
#         try:
#             client.utility.verify_payment_signature({
#                 "razorpay_order_id": razorpay_order_id,
#                 "razorpay_payment_id": razorpay_payment_id,
#                 "razorpay_signature": razorpay_signature,
#             })
#         except razorpay.errors.SignatureVerificationError:
#             return redirect("payment_failed")

#         # Create Order in Database
#         if buy_now:
#             Order.objects.create(
#                 user=request.user,
#                 product_id=buy_now["id"],
#                 quantity=buy_now["quantity"],
#                 total_price=buy_now["price"],
#                 address=address,
#             )
#         elif cart:
#             for product_id, item in cart.items():
#                 Order.objects.create(
#                     user=request.user,
#                     product_id=product_id,
#                     quantity=item["quantity"],
#                     total_price=item["price"] * item["quantity"],
#                     address=address,
#                 )

#         # Clear Session after Order is Placed
#         request.session.pop("checkout_address", None)
#         request.session.pop("buy_now", None)
#         request.session.pop("cart", None)
#         request.session.modified = True

#         return redirect("payment_success")


# working good
def complete_order(request):
    checkout_details = request.session.get("checkout_details")
    if not checkout_details:
        return redirect(checkout) 
    
    address = checkout_details["address"]
    mobile_number = checkout_details["mobile"]
    pincode = checkout_details["pincode"]

    buy_now = request.session.get("buy_now", None)
    cart = request.session.get("cart", {})
    
    print(f"BUY NOW: {buy_now}")  
    print(f"CART CONTENTS: {cart}") 

    if buy_now:
        product = get_object_or_404(Products, id=buy_now["id"])  # Get product
        if product.stock >= buy_now["quantity"]:  # Check stock availability
            Order.objects.create(
            user=request.user,
            product_id=buy_now["id"],
            quantity=buy_now["quantity"],
            total_price=buy_now["price"],
            address=address,
            mobile_number=mobile_number,
            pincode=pincode,
        )
            product.stock -= buy_now["quantity"]  # Reduce stock
            product.save()  # Save updated stock

            request.session.pop("buy_now", None)  
            request.session.pop("checkout_address", None)
            request.session.modified = True
            return redirect(order_success)
        else:
            messages.error(request, f"Only {product.stock} units available.")  
            return redirect("checkout")

    elif cart:  
        for product_id, item in cart.items():
            product = get_object_or_404(Products, id=product_id)  # Get product
            if product.stock >= item["quantity"]:  # Check stock availability
                Order.objects.create(
                    user=request.user,
                    product_id=product_id,
                    quantity=item["quantity"],
                    total_price=item["price"] * item["quantity"],
                    address=address,
                    mobile_number=mobile_number,
                    pincode=pincode,
                )
                product.stock -= item["quantity"]  # Reduce stock
                product.save()  # Save updated stock
            else:
                messages.error(request, f"Only {product.stock} units available for {product.name}.")  
                return redirect("checkout")  

        request.session.pop("cart", None)  

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
        quantity = int(request.POST.get("quantity", 1))
    else:
        quantity = 1 

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


def create_razorpay_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = int(float(data["amount"]) * 100)  

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create(
                {"amount": amount, "currency": "INR", "payment_capture": "1"}
            )

            return JsonResponse({"id": razorpay_order["id"], "amount": amount})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
def payment_success(request):
    return render(request, "user/payment_success.html")

def payment_failed(request):
    return render(request, "user/payment_failed.html")


# def complete_cod_order(request):
#     address = request.session.get("checkout_address")
    
#     if not address:
#         return redirect(checkout) 

#     buy_now = request.session.get("buy_now", None)
#     cart = request.session.get("cart", {})

#     print(f"BUY NOW: {buy_now}") 
#     print(f"CART CONTENTS: {cart}")

#     if buy_now:
#         Order.objects.create(
#             user=request.user,
#             product_id=buy_now["id"],
#             quantity=buy_now["quantity"],  
#             total_price=buy_now["price"],
#             address=address,
#         )
#         request.session.pop("buy_now", None)
#         request.session.pop("checkout_address", None)
#         request.session.modified = True
#         return redirect(order_success)
#     elif cart:
#         for product_id, item in cart.items():
#             Order.objects.create(
#                 user=request.user,
#                 product_id=product_id,
#                 quantity=item["quantity"],
#                 total_price=item["price"] * item["quantity"],
#                 address=address,
#             )
#         request.session.pop("checkout_address",None)
#         request.session.modified = True

#         return redirect(order_success)