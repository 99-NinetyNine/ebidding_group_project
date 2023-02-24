from django.contrib.auth.models import AbstractUser
from django.db import models
from django.shortcuts import reverse
import uuid

class User(AbstractUser):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    profile_pic= models.ImageField(default="default.jpg", upload_to="ProfileImages/")
    phone_num=models.PositiveBigIntegerField(null=True,blank=True,unique=True)
    bio=models.CharField(max_length=100,blank=False,null=True)
    latitude=models.CharField(max_length=20,blank=False,null=True)
    longitude=models.CharField(max_length=20,blank=False,null=True)
    phone_verified=models.BooleanField(default=False)
    

    
    def get_my_subscribers(self):
        #todo
        #use ai
        return User.objects.exclude(id=self.id)

    def has_verified_phone(self):
        return self.phone_verified

    def get_absolute_url(self):
        return reverse('profile_view', args=[str(self.id)])
    def get_update_url(self):
        return reverse('change_profile')
    def my_ratings(self):
        value=self.to.aggregate(models.Avg('rating'))
        return value['rating__avg']
        
        

class Rating(models.Model):
    id= models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    from_user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='src')
    to_user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='to')
    
    #useful for ai..show those users who u rated max
    RATING_CHOICES= [
        ('0','No rating'),
        ('1','Poor'),
        ('2','Satisfactory'),
        ('3','Good'),
        ('4','Better'),
        ('5','Excellent'),
    ]
    rating=models.CharField(
        max_length=1,
        choices=RATING_CHOICES,
        default='3',
    )
    def __str__(self):
        return self.from_user.username +" to " + self.to_user.username

# def bids_removed_alert(sender, instance, **kwargs):
#     if instance:
#         """
#         remove that notifin which says
#         x posted bid on auction y
        
#         instance.auction.user.bid_list.filter(user_by=instance.user,bid=instance.id or None,is_like=False).delete()
#         """


