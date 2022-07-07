from django.urls import reverse


def name_to_url(name_and_arg):
    return reverse(name_and_arg[0], args=name_and_arg[1])
