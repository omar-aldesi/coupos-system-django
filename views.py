def remove_coupon(request):
    order = Order.objects.get(user=request.user, ordered=False)
    CouponUser.objects.filter(user=request.user,coupon=order.coupon).update(used=F('used')- 1)
    order.coupon = None
    order.save()
    return redirect('core:order-summary')

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

class PaymentView(LoginRequiredMixin,TemplateView):
    def get(self,*args,**kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        context = {
            'order':order
        }
        return render(self.request,'pages/payment.html',context)
    
    def post(self,*args,**kwargs):
  
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100) 

        try:
            charge = stripe.Charge.create(
            amount= amount,
            currency="usd",
            description="My second Test Charge (created for API docs)",
            source= token, # obtained with Stripe.js
            )
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()


            order_items = order.items.all()
            order_items.update(ordered=True)

            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request,'Your order was successful')
            return redirect('/')
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            Error.objects.create(
                error_type="CardError",
                error_message="Error",
                error_date = timezone.now(),
                error_status = 'CardError'
            )
            return redirect("/")

        except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            Error.objects.create(
                error_type="Rate limit error",
                error_message="Error",
                error_date = timezone.now(),
            )
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
            print(e)
            messages.warning(self.request, "Invalid parameters")
            Error.objects.create(
                error_type="Invalid parameters",
                error_message="Error",
                error_date = timezone.now(),
            )
            return redirect("/")

        except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            Error.objects.create(
                error_type="Not authenticated",
                error_message="Error",
                error_date = timezone.now(),
            )
            return redirect("/")

        except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            Error.objects.create(
                error_type="Network error",
                error_message="Error",
                error_date = timezone.now(),
            )
            return redirect("/")

        except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
            messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
            Error.objects.create(
                error_type="Stripe Error",
                error_message="Something went wrong. You were not charged. Please try again.",
                error_date = timezone.now(),
            )
            return redirect("/")

        except Exception as e:
                # send an email to ourselves
            messages.warning(
                self.request, "A serious error occurred. We have been notifed.")
            Error.objects.create(
                error_type="Stripe Error",
                error_message="A serious error occurred. We have been notifed.",
                error_date = timezone.now(),
            )
            return redirect("/")
