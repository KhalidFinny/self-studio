from django.db import models

class Capture(models.Model):
    image = models.ImageField(upload_to='captures/')
    timestamp = models.DateTimeField(auto_now_add=True)
    gesture = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Capture {self.id} at {self.timestamp}"
