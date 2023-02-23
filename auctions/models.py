from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core import validators
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

import uuid

from django.utils import timezone
import datetime

from django.conf import settings

from django.shortcuts import reverse

from PIL import Image


# class Place(models.Model):
#     city = models.CharField(max_length=100)
#     location = PlainLocationField(based_fields=['city'], zoom=7)

class Estate(models.Model):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="estate")
    title=models.CharField(max_length=30,blank=False,null=True)
    description = models.CharField(max_length=200, blank=False,null=True)

    #location = models.OneToOneField(Place, on_delete=models.CASCADE)
    
    upvotes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="likes", blank=True)
    downvotes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="dislikes", blank=True)
    favourite = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="favourites", blank=True)
    hide_post = models.BooleanField(default=False, blank=True)
    
    
    price_min_value= models.IntegerField(default=1)
    price_max_value=models.IntegerField(default=100)

    pub_date = models.DateTimeField(default=timezone.now)
    expiry_date=models.DateTimeField(default=timezone.now)  #put it 7 days later
        

    class Meta:
        ordering = ["-pub_date"]

    def __str__(self):
        return self.user.username +" auction %s" %str(self.id)[0:4]

    def total_upvotes(self):
        return self.upvotes.count()

    def get_absolute_url(self):
        return reverse("auction_detail", args=[str(self.id)])

    def has_expired(self):
        if(self.expiry_date<= timezone.now()):
            return False
        return True


class EstateImage(models.Model):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name="media")
    about = models.CharField(max_length=50, blank=True,null=True)
    photo = models.FileField(upload_to="EstateImages/", blank=True, null=True)
    is_photo = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return "gallery%s" %str(self.id)[0:4]
    def get_absolute_url(self):
        return reverse('image_link', args=[str(self.id)])


class Bids(models.Model):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="bid_list")
    estate=models.ForeignKey(Estate, on_delete=models.CASCADE,related_name="bids")
    bid_amount=models.FloatField(default=0)

    def get_absolute_url(self):
        return reverse('bid_detail', args=[str(self.id)])
    def __str__(self):
        return self.user.username+" bid %s" %str(self.id)[0:4]
    
    class Meta:
        pass
        # constraints = [
        #     models.CheckConstraint(
        #         check=(models.Q(bid_amount__gte=estate.price_min_value) & models.Q(bid_amount__lte<=estate.price_max_value)), name='bid_range'),
        #     models.CheckConstraint(
        #         check=(models.Q(estate__.has_expired)),name='not_expired'),
        # ]
    
    # def clean(self):
    #         if not( ):
    #             raise ValidationError({
    #                 'bid_amount': ValidationError('Out of range', code='invalid'),
    #             })
    #         if (self.estate.has_expired()):
    #             raise ValidationError({
    #                 'estate': ValidationError('Expired auction.', code='invalid'),
    #             })



class Notification(models.Model):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="bids_alert", on_delete=models.CASCADE, default=None
    )
    other_user= models.ForeignKey(
        settings.AUTH_USER_MODEL,on_delete=models.CASCADE,blank=True,null=True, default=None
    )

    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, null=True,blank=True)
    bid=models.ForeignKey(Bids,on_delete=models.CASCADE,null=True,blank=True)

    created=models.DateTimeField(default=timezone.now)

    is_like = models.BooleanField(default=False, blank=True)
    is_checked=models.BooleanField(default=False, blank=True)
    """
    to check like:
        is_like
    
    to check estate:
        (estate and not bid)
    
    to check bid:
        (bid and not estate)
    
    a little optimization than:

    is_bid= models.BooleanField(default=False, blank=True,null=True)
    is_auction= models.BooleanField(default=False, blank=True,null=True)
    
    """
    class Meta:
        ordering = ["-created"]

    def __str__(self):
        msg=""
        if(self.is_like):
            msg="like"
        elif(self.estate and not self.bid):
            msg="auction"
        elif(self.bid):
            msg="bid"

        msg= msg+" "+"notification %s" %str(self.id)[0:4]
        return msg
    def get_absolute_url(self):
        return reverse('notification_detail', args=[str(self.id)])