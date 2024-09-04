from tortoise import fields
from tortoise.models import Model
from enum import Enum
import datetime

class InteractionType(str, Enum):
    LIKE = "like"
    SKIP = "skip"

class User(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField(unique=True)
    username = fields.CharField(max_length=50, null=True)
    first_name = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    full_name = fields.CharField(max_length=100, null=True)
    birth_date = fields.DateField(null=True)
    description = fields.TextField(null=True)
    main_username = fields.CharField(max_length=50, null=True)
    photos = fields.JSONField(null=True)
    channel = fields.CharField(max_length=100, null=True)
    rating_sum = fields.IntField(default=0)
    rating_count = fields.IntField(default=0)
    referral_count = fields.IntField(default=0)  # Счётчик рефералов

    @property
    def age(self):
        if self.birth_date:
            today = datetime.date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    
    @property
    def rating(self):
        if self.rating_count > 0:
            return self.rating_sum / self.rating_count
        return 0

    def __str__(self):
        return f"{self.full_name} ({self.username})"

class UserInteraction(Model):
    user = fields.ForeignKeyField("models.User", related_name="interactions")
    target_user = fields.ForeignKeyField("models.User", related_name="interacted_by")
    interaction_type = fields.CharEnumField(enum_type=InteractionType)
    created_at = fields.DatetimeField(auto_now_add=True)

class Match(Model):
    user1 = fields.ForeignKeyField("models.User", related_name="matches_as_user1")
    user2 = fields.ForeignKeyField("models.User", related_name="matches_as_user2")
    created_at = fields.DatetimeField(auto_now_add=True)

class Rating(Model):
    user = fields.ForeignKeyField("models.User", related_name="ratings")
    rated_by = fields.ForeignKeyField("models.User", related_name="given_ratings")
    score = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
