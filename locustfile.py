"""Locust load test: Posts CRUD (list, create, update, delete)."""
from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import random
import string
import os

try:
    from locust_metrics_collector import init_metrics_collector
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    print("Metrics collector not available. Install psutil for memory tracking: pip install psutil")


class PostsUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.get("/posts/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_token:
                self.csrf_token = csrf_token.get('value')
            else:
                self.csrf_token = response.cookies.get('csrftoken', '')
        else:
            self.csrf_token = ''
        self.created_post_ids = []
    
    def get_csrf_token(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            return csrf_input.get('value')
        return response.cookies.get('csrftoken', '')
    
    def generate_random_string(self, length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @task(3)
    def view_post_list(self):
        with self.client.get("/posts/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load post list: {response.status_code}")
    
    @task(2)
    def create_post(self):
        form_response = self.client.get("/posts/create/")
        csrf_token = self.get_csrf_token(form_response)
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')

        title = f"Test Post {self.generate_random_string(8)}"
        author = f"Author {self.generate_random_string(6)}"
        headers = {
            'X-CSRFToken': csrf_token,
            'Referer': f"{self.host}/posts/create/"
        }
        
        with self.client.post(
            "/posts/create/",
            data={
                'title': title,
                'author': author,
                'csrfmiddlewaretoken': csrf_token
            },
            headers=headers,
            cookies=form_response.cookies,
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Failed to create post: {response.status_code}")
    
    @task(1)
    def update_post(self):
        list_response = self.client.get("/posts/")
        if list_response.status_code != 200:
            return
        soup = BeautifulSoup(list_response.text, 'html.parser')
        update_links = soup.find_all('a', href=lambda x: x and '/posts/update/' in x)
        if not update_links:
            return
        update_url = update_links[0].get('href')
        post_id = update_url.split('/')[-2] if update_url else None
        
        if not post_id:
            return
        form_response = self.client.get(f"/posts/update/{post_id}/")
        csrf_token = self.get_csrf_token(form_response)
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')
        title = f"Updated Post {self.generate_random_string(8)}"
        author = f"Updated Author {self.generate_random_string(6)}"
        
        headers = {
            'X-CSRFToken': csrf_token,
            'Referer': f"{self.host}/posts/update/{post_id}/"
        }
        
        with self.client.post(
            f"/posts/update/{post_id}/",
            data={
                'title': title,
                'author': author,
                'csrfmiddlewaretoken': csrf_token
            },
            headers=headers,
            cookies=form_response.cookies,
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Failed to update post: {response.status_code}")
    
    @task(1)
    def delete_post(self):
        list_response = self.client.get("/posts/")
        if list_response.status_code != 200:
            return
        soup = BeautifulSoup(list_response.text, 'html.parser')
        delete_links = soup.find_all('a', href=lambda x: x and '/posts/delete/' in x)
        if not delete_links:
            return
        delete_url = delete_links[0].get('href')
        post_id = delete_url.split('/')[-2] if delete_url else None
        if not post_id:
            return
        form_response = self.client.get(f"/posts/delete/{post_id}/")
        csrf_token = self.get_csrf_token(form_response)
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')
        headers = {
            'X-CSRFToken': csrf_token,
            'Referer': f"{self.host}/posts/delete/{post_id}/"
        }
        
        with self.client.post(
            f"/posts/delete/{post_id}/",
            data={'csrfmiddlewaretoken': csrf_token},
            headers=headers,
            cookies=form_response.cookies,
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Failed to delete post: {response.status_code}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if METRICS_ENABLED:
        try:
            django_pid = os.environ.get('DJANGO_PID', None)
            if django_pid:
                django_pid = int(django_pid)
            
            output_dir = os.environ.get('LOCUST_METRICS_DIR', 'results')
            init_metrics_collector(django_pid=django_pid, output_dir=output_dir, environment=environment)
            print("Metrics collector initialized")
        except Exception as e:
            print(f"Warning: metrics collector failed: {e}")

