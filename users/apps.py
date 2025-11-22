from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = 'Users'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """Se ejecuta cada vez que se levanta el servidor Django."""
        #import users.signals
        """from django.db.utils import OperationalError, ProgrammingError
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_migrate
        from django.dispatch import receiver
        from users.models import Profile
        from django.db.models.signals import post_save
        from django.contrib.auth.models import User



        def create_admin_user(sender, **kwargs):
            try:
                User = get_user_model()
                if not User.objects.filter(username='admin').exists():
                    User.objects.create_superuser(
                        username='admin',
                        email='admin@example.com',
                        password='admin123'
                    )
                    print(" Superusuario creado automáticamente (admin / admin123)")
            except (OperationalError, ProgrammingError):
                print(" No se pudo crear el superusuario (DB no lista todavía)")

        @receiver(post_save, sender=User)
        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                Profile.objects.create(user=instance)
                print(f"Perfil creado automáticamente para el usuario {instance.username}")

        # Conectar la señal
        post_migrate.connect(create_admin_user, sender=self)
        post_migrate.connect(create_user_profile, sender=self)"""
        

