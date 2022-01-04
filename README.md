# coupos-system-django

note:
you need this models before start:

```python

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True,null=True)
    orderd_date = models.DateTimeField(null=True,default=datetime.datetime.now)
    ordered = models.BooleanField(default=False)
    shippingmethod = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE,null=True,blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    billingadress = models.OneToOneField(BillingAdress, on_delete=models.CASCADE,null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)

class OrderItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    ordered = models.BooleanField(default=False)
```

lets start:
the first step create models:


```python

class Coupon(models.Model):
    code = models.CharField(max_length=15, unique=True)
    active = models.BooleanField(default=True)
    valid_to = models.DateField(blank=True,null=True,default=datetime.datetime.now().strftime("%Y-%m-%d"))
    coupon_type = models.CharField(max_length=10, choices=COUPON_CHOICES, default='monetary')
    amount = models.FloatField()
    user_limit = models.PositiveIntegerField(("User limit"), default=1)

    def __str__(self):
        return self.code


class CouponUser(models.Model):
    coupon = models.ForeignKey(Coupon, related_name='users', on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name=("User"), null=True, blank=True, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(("Redeemed at"), blank=True, null=True)
    used = models.IntegerField(default=0)

    class Meta:
        unique_together = (('coupon', 'user'),)

    def __str__(self):
        return str(self.user)
```

and add coupon choices in model.py

```python

COUPON_CHOICES =(
    ('monetary', 'Money based coupon'),
    ('percentage', 'Percentage discount'),
)

```
to calculate the amount:

you can add this fun to Total Calculation fun:

```python
        try:
            if self.coupon.coupon_type == 'monetary':
                total -= self.coupon.amount
            elif self.coupon.coupon_type == 'percentage':
                a = (self.coupon.amount / 100) * total
                total -= a
        except:
            pass

        try:
            if self.coupon.coupon_type == 'monetary':
                if self.coupon.amount > total:
                    total = 0
        except:
            pass
```

now in views.py:

get the coupon from template
```python
def get_coupon(request, code):
    if Coupon.objects.filter(code=code,active=True).exists():
        try:
            coupon = Coupon.objects.get(code=code)
            check_valid = coupon.valid_to
            int(str(check_valid).replace("-",""))
            now = dateformat.format(timezone.now(), 'Ymd') # true
            is_valid_coupon = int(str(check_valid).replace("-",""))

            if is_valid_coupon < int(now):
                Error.objects.create(
                    error_type="Coupon Expired",
                    error_message="The coupon you are trying to use has expired",
                    error_date = timezone.now(),
                    error_status = 'Expired Coupon '+ str(coupon.code),
                )
                coupon.active = False
                coupon.save()
                messages.info(request, "The coupon you are trying to use has expired")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

            elif is_valid_coupon > int(now):
                return coupon

            else:
                messages.info(request, "something went wrong")
                Error.objects.create(
                    error_type="Coupon Error",
                    error_message="something went wrong",
                    error_date = timezone.now(),
                )
                return None

        except ObjectDoesNotExist:
            return None
    else:
        return None
```

remove coupon from order:
```python
def remove_coupon(request):
    order = Order.objects.get(user=request.user, ordered=False)
    CouponUser.objects.filter(user=request.user,coupon=order.coupon).update(used=F('used')- 1)
    order.coupon = None
    order.save()
    return redirect('core:order-summary')
```
add coupon:

```python
class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if get_coupon(self.request, self.request.POST['code']) is not None:
            if form.is_valid():
                try:
                    code = form.cleaned_data.get('code')
                    check_user = CouponUser.objects.filter(user=self.request.user, coupon=get_coupon(self.request, code)).exists()
                    if check_user:
                        pass
                    else:
                        CouponUser.objects.create(
                            user=self.request.user,
                            coupon=get_coupon(self.request, code),
                            redeemed_at=timezone.now(),
                        )
                    try:
                        check_user_limit = CouponUser.objects.get(user=self.request.user,coupon=get_coupon(self.request, code))
                        coupon = Coupon.objects.get(code=get_coupon(self.request, code))
                    except ObjectDoesNotExist:
                        messages.info(self.request, "something went wrong")
                    order = Order.objects.get(user=self.request.user, ordered=False)
                    try:
                        if coupon.user_limit <= check_user_limit.used:
                            messages.info(self.request, "You have reached the limit of this coupon")
                            return redirect('core:order-summary')
                        else:
                            try:
                                if Order.objects.filter(user=self.request.user, ordered=False,coupon=get_coupon(self.request, code)).exists():
                                    messages.info(self.request, "This coupon has been applied")
                                    return redirect('core:order-summary')
                                else:
                                    if check_user:
                                        order.coupon = get_coupon(self.request, code)
                                        order.save()
                                        CouponUser.objects.filter(user=self.request.user, coupon=get_coupon(self.request, code)).update(used=F('used')+1)
                                        messages.success(self.request, "Successfully added coupon")
                                        return redirect('core:order-summary')
                                    else:
                                        CouponUser.objects.filter(user=self.request.user, coupon=get_coupon(self.request, code)).update(used=F('used')+1)
                                        order.coupon = get_coupon(self.request, code)
                                        order.save()
                                        messages.success(self.request, "Successfully added coupon")
                                        return redirect('core:order-summary')
                            except:
                                messages.info(self.request, "something went wrong")
                                return redirect('core:order-summary')
                    except:
                        return redirect("core:order-summary") # here the checkout page
                except ObjectDoesNotExist:
                    messages.info(self.request, "You do not have an active order")
                    return redirect("core:order-summary") # here the checkout page
            else:
                messages.info(self.request, "method not allowed")
                return redirect("core:order-summary")
        else:
            messages.info(self.request, "The coupon you are trying to use does not exist")
            return redirect("core:order-summary")
```

in urls.py:
```python
    path('add-coupon/',views.AddCouponView.as_view(),name='add-coupon'),
    path('remove-coupon/',views.remove_coupon,name='remove-coupon'),
```

in forms.py:

simple coupon form
```python
class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        # some attrs 
        'placeholder':'promocode',
        'aria-label':'Recipient\'s username',
        'aria-describedby':'basic-addon2',
    }))
```
now in the template:

add coupon:
```html
  <form method="post" action="{% url 'core:add-coupon' %}"> <!--important-->
    {% csrf_token %}
    {{couponform.code}}
    <button type="submit">Apply</button>
  </form>
```

remove coupon:
```python
   {% if object.coupon %}                                 
    <a class="btn karl-checkout-btn" href="{% url 'core:remove-coupon' %}">remove coupon</a>
   {% endif %}
```
