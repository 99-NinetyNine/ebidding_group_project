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

from celery import shared_task

import random
from mechanism.users import User
# class Place(models.Model):
#     city = models.CharField(max_length=100)
#     location = PlainLocationField(based_fields=['city'], zoom=7)


class AuctionManager(models.Manager):
    def get_queryset_for(self,user):
        return self.get_queryset()
    
    def inventory_incharge_created(self,some_inventory_officer):
        return self.get_queryset().filter(user=some_inventory_officer)
    def waiting_for_admin(self,some_admin):
        from mechanism.auction_admin_waiting import AdminWaitingAuction
        waiting_list=AdminWaitingAuction.objects.all()
        res=[]
        for item in waiting_list:
            print("hello")
            if item.auction.disclosed_by_particular_admin(some_admin):
                continue
            print("hi")
            res.append(item.auction)
        
        return res

    def for_index_page(self):
        qs=self.get_queryset()
        rd=random.randint(0,len(qs))
        new=qs[0:rd]
        old=qs[rd:]
        return new,old


    def get_serialized_query_set(self,query_set,request,single_item=False):
        """
        returns a list of ["auction instance","is_liked","is_disliked","is_favourite"]
        """
        res=[]
        
        if(single_item):
            res.append(query_set)
            res.append(query_set.upvotes.filter(id=request.user.id).exists())
            res.append(query_set.downvotes.filter(id=request.user.id).exists())
            res.append(query_set.favourite.filter(id=request.user.id).exists())
            
            #note that i need list of lists haha..for unpacking
            res2=[]
            res2.append(res)
            return res2


        for q in query_set:
            t=[]
            t.append(q)
            t.append(q.upvotes.filter(id=request.user.id).exists())
            t.append(q.downvotes.filter(id=request.user.id).exists())
            t.append(q.favourite.filter(id=request.user.id).exists())
            res.append(t)
        
        return res



    def get_highest_bidder(self,auction):
        if auction.exists_in_admin_waiting_bucket() or auction.exists_in_dead_bucket() or auction.exists_in_re_schedule_bucket():
            return None
        if auction.exists_in_not_settled_bucket():
            return auction.not_settled.get_current_winner()
        
        elif auction.exists_in_live_bucket():
            if(auction.is_type_open()):
                return auction.bids.all().order_by("-bid_amount").first()
            else:
                None
    
class Auction(models.Model):
    id= models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    query=AuctionManager()
    objects=models.Manager()
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auction")
    title=models.CharField(max_length=30,blank=False,null=True)
    description = models.CharField(max_length=200, blank=False,null=True)
    youtube=models.CharField(max_length=100,blank=True,null=True)
    thumbnail=models.ImageField(upload_to="AuctionImages/",null=True,)
    #
    open_close=models.BooleanField(default=False)
    #false=open
    #
    
    saved_confirmed=models.BooleanField(default=False)
    #false=saved
    
    #product
    product_shipped=models.BooleanField(default=False)

    #location = models.OneToOneField(Place, on_delete=models.CASCADE)
    upvotes = models.ManyToManyField(User, related_name="likes", blank=True)
    downvotes = models.ManyToManyField(User, related_name="dislikes", blank=True)
    favourite = models.ManyToManyField(User, related_name="favourites", blank=True)
    hide_post = models.BooleanField(default=False, blank=True)
    

    pdf=models.FileField(upload_to="Auction_pdf/")
    price_min_value= models.IntegerField(default=1)
    price_max_value=models.IntegerField(default=100)

    pub_date = models.DateTimeField(default=timezone.now)
    expiry_date=models.DateTimeField(default=timezone.now)  #put it 7 days later

    

    class Meta:
        ordering = ["-pub_date"]
    #############               BUCKETS LOGIC HERE                      #############
    #############               BUCKETS LOGIC HERE                      #############
    #############               BUCKETS LOGIC HERE                      #############
    
    #test
    def get_highest_bid_amount(self):
        return 100
    #test
    def move_to_live(self):
        try:
            self.pop_from_live_bucket()
        except:
            try:
                self.pop_from_admin_waiting_bucket()
            except:
                try:
                    self.pop_from_not_settled_bucket()
                except:
                    try:
                        self.pop_from_re_schedule_bucket()
                    except:
                        try:
                            self.pop_from_settled_bucket()
            
                        except Exception as e:
                            print(e)
                            return
    
        self.push_to_live_bucket()

    def move_to_admin_waiting(self):
        try:
            self.pop_from_live_bucket()
        except:
            try:
                self.pop_from_admin_waiting_bucket()
            except:
                try:
                    self.pop_from_not_settled_bucket()
                except:
                    try:
                        self.pop_from_re_schedule_bucket()
                    except:
                        try:
                            self.pop_from_settled_bucket()
            
                        except Exception as e:
                            print(e)
                            return

        from mechanism.auction_admin_waiting import AdminWaitingAuction
        AdminWaitingAuction.objects.create(auction=self)

    def move_to_not_settled(self):
        try:
            self.pop_from_live_bucket()
        except:
            try:
                self.pop_from_admin_waiting_bucket()
            except:
                try:
                    self.pop_from_not_settled_bucket()
                except:
                    try:
                        self.pop_from_re_schedule_bucket()
                    except:
                        try:
                            self.pop_from_settled_bucket()
            
                        except Exception as e:
                            print(e)
                            return
        from mechanism.auction_not_settled import NotSettledAuction
        NotSettledAuction.objects.create(auction=self)


    def move_to_settled(self):
        try:
            self.pop_from_live_bucket()
        except:
            try:
                self.pop_from_admin_waiting_bucket()
            except:
                try:
                    self.pop_from_not_settled_bucket()
                except:
                    try:
                        self.pop_from_re_schedule_bucket()
                    except:
                        try:
                            self.pop_from_settled_bucket()
            
                        except Exception as e:
                            print(e)
                            return
        from mechanism.auction_settled import SettledAuction
        SettledAuction.objects.create(auction=self)

    def move_to_reschedule(self):
        try:
            self.pop_from_live_bucket()
        except:
            try:
                self.pop_from_admin_waiting_bucket()
            except:
                try:
                    self.pop_from_not_settled_bucket()
                except:
                    try:
                        self.pop_from_re_schedule_bucket()
                    except:
                        try:
                            self.pop_from_settled_bucket()
            
                        except Exception as e:
                            print(e)
                            return
        
        from mechanism.auction_reschedule import RescheduleAuction
        RescheduleAuction.objects.create(auction=self)


    ################################         #REAL ONES         ################################         
    ################################                            ################################         
    
    ##live
    def push_to_live_bucket(self):
        from mechanism.auction_live import LiveAuction
        LiveAuction.objects.create(auction=self)


    def pop_from_live_bucket(self):
        self.live.delete()
        
    def exists_in_dead_bucket(self):
        ##case when inventory incharge just saves but donot broadcast
        ##for any reason 
        return False

    def exists_in_live_bucket(self):
        try:
            live=self.live
        except Exception as e:
            print(e)
            return False
        
        return True
    
    ##admin waiting
    ##before pushing, it must be in just(previous) before bucket and it is removed from old bucket.
    def push_to_admin_waiting_bucket(self):
        from mechanism.auction_admin_waiting import AdminWaitingAuction

    
        #first pop from live
        assert self.exists_in_live_bucket()==True
        self.pop_from_live_bucket()
        
        AdminWaitingAuction.objects.create(auction=self)

        print("inconsistent",e)

    def pop_from_admin_waiting_bucket(self):
        self.waiting_admin.delete()
        
    def exists_in_admin_waiting_bucket(self):
        try:
            admin_waiting_bucket=self.waiting_admin
        except Exception as e:
            print(e)
            return False
        
        return True


    ##not_setttled
    def push_to_not_settled_bucket(self):
        from mechanism.auction_not_settled import NotSettledAuction
        
        if(self.is_type_open()):
            assert self.exists_in_live_bucket() is True
            self.pop_from_live_bucket()
        else:
            assert self.exists_in_admin_waiting_bucket() is True
            self.pop_from_admin_waiting_bucket()
        
        NotSettledAuction.objects.create(auction=self)
        

    def pop_from_not_settled_bucket(self):
        self.not_settled.delete()
        
    def exists_in_not_settled_bucket(self):
        try:
            not_settled_bucket=self.not_settled
        except Exception as e:
            print(e)
            return False
        
        return True

    ##setttled
    def push_to_settled_bucket(self):
        from mechanism.auction_settled import SettledAuction
        
        assert self.exists_in_not_settled_bucket() is True
        self.pop_from_not_settled_bucket()
        SettledAuction.objects.create(auction=self,winner=self.get_highest_bidder().bidder)

    def pop_from_settled_bucket(self):
        self.settled.delete()
        
    def exists_in_settled_bucket(self):
        try:
            settle=self.settled
        except Exception as e:
            print(e)
            return False
        
        return True

    ##reschedule
    def push_to_re_schedule_bucket(self):
        from mechanism.auction_reschedule import RescheduleAuction
        
        assert self.exists_in_not_settled_bucket() is True
        assert self.exists_in_admin_waiting_bucket() is False
        assert self.exists_in_settled_bucket() is False
        assert self.exists_in_live_bucket() is False

        self.pop_from_not_settled_bucket()
        RescheduleAuction.objects.create(auction=self)

    def pop_from_re_schedule_bucket(self):
        self.re_schedule.delete()
        
    def exists_in_re_schedule_bucket(self):
        try:
            settle=self.re_schedule
        except Exception as e:
            print(e)
            return False
        
        return True

    def recyle_to_live(self):
        assert self.exists_in_re_schedule_bucket()
        self.pop_from_re_schedule_bucket()
        LiveAuction.objects.create(auction=self)

        
    #############               CHECKERS LOGIC STARTS HERE                      #############
    #############               CHECKERS LOGIC STARTS HERE                      #############
    #############               CHECKERS LOGIC STARTS HERE                      #############
    #############               CHECKERS LOGIC STARTS HERE                      #############
    def is_type_open(self):
        return self.open_close #open=1,close=0
    def does_he_have_bid(self,some_user):
        exists=False
        amount=None
        tuple=None
        qs= self.bids.filter(bidder=some_user)
        if qs.exists():
            tuple=qs.first()
            amount=tuple.bid_amount
            
            if(amount>0):
                exists=True
            print("your bdidis",amount)
        
        return exists, amount,tuple

    def disclosed_by_admins(self):
        try:
            waiting=self.waiting_admin
        except Exception as e:
            print(e)
            return False
        return waiting.semaphore==0


    
    def has_product_shipped(self):
        return False

    def bidder_paid_initial(self,bidder):
        try:
            tuple=self.bids.filter(bidder=bidder)
            if(tuple.exists()):
                return tuple.first().initial_paid()
        except Exception as e:
            print(e)

        return False
    
    

    def disclosed_by_particular_admin(self,some_admin=None):
        try:
            if some_admin.is_admin_A:
                if  self.waiting_admin.adminA_entered_otp():
                    return True
                else:
                    return False
            if  some_admin.is_admin_B:
                if self.waiting_admin.adminB_entered_otp():
                    return True
                else:
                    return False
            if some_admin.is_admin_C:
                if self.waiting_admin.adminC_entered_otp():
                    return True
                else:
                    return False
                
        except Exception as e:
            print(e)
            return False
        
        return True

    def is_new_bid_okay(self,bid_amount,bidder=None):
        if(not self.is_type_open()):
            return True
        highest_bidding=self.get_highest_bidder()
        
        
        if(highest_bidding.bid_amount <= float(bid_amount)):
            return False
        
        return True



  
    def has_expired(self):
        if(self.expiry_date<= timezone.now()):
            return False
        return True

    
    def check_otp_for_admins(self,admin,some_otp):
        return True

    

    #############               GETTERS LOGIC STARTS HERE                      #############
    #############               GETTERS LOGIC STARTS HERE                      #############
    #############               GETTERS LOGIC STARTS HERE                      #############
    #############               GETTERS LOGIC STARTS HERE                      #############
    

    def __str__(self):
        return self.user.username +" auction %s" %str(self.id)[0:4]

    #test
    def play_accountant_role(self):
        highest=self.get_highest_bidder()
        
        quote=highest.bid_amount
        deposited=self.price_min_value
        to_pay=quote-deposited
        return to_pay,deposited,quote
    
    def get_formated_expiry_date(self):
        return "0d  : 11h  : 23m  : 29s"
    def get_formated_starting_date(self):
        return "0d  : 11h  : 23m  : 29s"

    def get_expiry_date(self):
        return "2023/3/22"
    def get_expired_date(self):
        return "2023/2/22"
    def get_remaining_amount_to_pay(self):
        return 100
    def get_collateral_amount(self):
        return 100
    def get_price_paid_to_won(self):
        return 100
    
    def get_bid_increment_allowed(self):
        return 50
    def get_current_maximun_bid_amount(self):
        return 50


    
    def get_number_of_bids(self):
        
        try:
            return self.bids.all().count()
        except Exception as e:
            print(e)
            return 0
    def get_bids_by_order(self):
        return self.bids.all().order_by("-bid_amount")

    def get_youtube(self):
        y1=["asda ","asdasdH-X81"]
        youtube=random.choice(y1)
        #return f"https://www.youtube.com/embed/{self.youtube}?autoplay=1&mute=1&loop=1&controls=0"
        return f"https://www.youtube.com/embed/{youtube}?autoplay=1&mute=1&loop=1&controls=0"
        
    def get_highest_bidder(self):
        return Auction.query.get_highest_bidder(self)

    def get_absolute_url(self):
        return reverse("auction_detail", args=[str(self.id)])

    def get_otp_for_admins(self):
        print("otp are",1102,1021,1212)
        return 112,121,1212

    
    def total_upvotes(self):
        return self.upvotes.count()

    def get_amount_he_bid(self,some_user):
        return self.bids.filter(bidder=some_user).first().bid_amount
    
    def get_bid_winner(self):
        biddings=self.bids.all()
        highest=biddings.first()
        for bidding in biddings:
            if bidding.bid_amount > highest.bid_amount:
                highest=bidding
        
        return highest.bidder

    #############               SETTERS LOGIC STARTS HERE                      #############
    #############               SETTERS LOGIC STARTS HERE                      #############
    #############               SETTERS LOGIC STARTS HERE                      #############
    #############               SETTERS LOGIC STARTS HERE                      #############
    
    def handle_another_admin_entered_otp(self,some_admin):
        index="0" if some_admin.is_admin_A else "1" if some_admin.is_admin_B else "2"
        return self.waiting_admin.down_semaphore(index=index)

    def some_admin_entered_otp(self):
        if self.exists_in_admin_waiting_bucket() \
            and self.waiting_admin.down_semaphore():
            
            return True
        
        return False
    def increase_cutoff(self):
        return 1
    def mark_expired(self):
        pass
        #do something


    
    #############               SCHEDULABLE LOGIC STARTS HERE                      #############
    #############               SCHEDULABLE LOGIC STARTS HERE                      #############
    #############               SCHEDULABLE LOGIC STARTS HERE                      #############
    #############               SCHEDULABLE LOGIC STARTS HERE                      #############
    
    #expireation riggered, then excecute these fucntions    
    @staticmethod
    @shared_task()
    ##@###haha critical section i love deadlocks!!
    def beat_beat():
        #run every 10 minutes
        from mechanism.auction_live import LiveAuction
        
        
        for tuple in LiveAuction.objects.all():
            if(tuple.time_to_expire()):
                tuple.auction.handle_auction_expiration()
        
        ##noe same goes for 7 days logic
        from mechanism.auction_not_settled import NotSettledAuction
        print("ok import fine")
        for tuple in NotSettledAuction.objects.all():
            
            if tuple.seven_days_elapsed():

                tuple.auction.handle_winner_was_a_liar()

    def handle_auction_expiration(self):
        self.mark_expired()
        
        bid_winner=self.get_bid_winner()

        #2
        self.notify_that_auction_expired()

        #3
        if(bid_winner is None):
            self.handle_no_bidder()
            return

        if self.is_type_open():
            self.push_to_not_settled_bucket()
        else:
            self.push_to_admin_waiting_bucket()
        

    def handle_no_bidder(self):
        self.pop_from_live_bucket()
        
        #this is not good
        from mechanism.auction_resch import RescheduleAuction
        
        print("no bidder")
        RescheduleAuction.objects.create(auction=self)
        
        self.notify_that_no_bidder_till_expiry()
    

    
    
    def handle_winner_was_a_liar(self):
        #1
        from mechanism.bid_liars import LiarBidder
        winner=self.get_bid_winner()
        LiarBidder.objects.create(auction=self,liar=winner)
        
        #2
        bid_of_liar=self.bids.filter(bidder=winner)
        bid_of_liar.charge_fine()
        
        #3
        self.notify_that_winner_was_liar(winner)

        #4
        #find next bidder
        next_winner=self.get_next_bidder()

        #5
        if(next_winner):
            self.notify_we_have_new_winner(next_winner)
        else:
            self.push_to_re_schedule_bucket()



    #############               NOTICE LOGIC STARTS HERE                      #############
    #############               NOTICE LOGIC STARTS HERE                      #############
    #############               NOTICE LOGIC STARTS HERE                      #############
    #############               NOTICE LOGIC STARTS HERE                      #############
    #notifications
    def notify_that_no_bidder_till_expiry(self):
        print("notify_that_no_bidder_till_expiry(self):")
        
    def new_like_notification(self,liker):
        from .notification import Notification
        Notification.objects.create_for_new_like(self.user, liker)
    def send_notice_to_page(self):
        print("notify this happednd,send_notice_to_news")
    
    def send_notice_to_news(self):
        print("notify this happednd,send_notice_to_news")

    def notify_to_winner(self,winner):
        print("notify this happednd,notify_to_winner")

    def notify_that_auction_is_created(self):
        print(" notify_that_auction_is_created")

    def notify_that_auction_expired(self):
        print("auction has expired please notify to , bid winner, notice page and others")

    def notify_that_winner_was_liar(self,liar):
        print("notify this happednd,notify_that_winner_was_liar")
    
    def notify_we_have_new_winner(self,new_winner):
        print("notify this happednd,notify_we_have_new_winner")

    


    

    #############               SERIALIZING  LOGIC STARTS HERE                      #############
    #############               SERIALIZING  LOGIC STARTS HERE                      #############

    def prepare_for_index_page(self,request=None):
        
        t=self.__dict__
        t["db"]=self
        t["fav"]=self.favourite.filter(id=request.user.id if request else 0).exists()    
        #print(t)
        return t
    
    

    def prepare_for_detail_page(auction):
        return auction
    
    
    ####SUPER CHHECKER
    def super_checker(self):
        haha=self.exists_in_live_bucket()\
        +self.exists_in_admin_waiting_bucket\
        +self.exists_in_not_settled_bucket()\
        +self.exists_in_settled_bucket()\
        +self.exists_in_re_schedule_bucket()

        try:
            assert haha==1
            print("We are in good state")
        except:
            print("we are in inconsistent state")

