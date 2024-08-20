from tortoise import fields
from tortoise.models import Model
import datetime

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

    @property
    def age(self):
        if self.birth_date:
            today = datetime.date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def __str__(self):
        return f"{self.full_name} ({self.username})"
