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
