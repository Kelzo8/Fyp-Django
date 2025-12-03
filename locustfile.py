"""
Locust load testing file for Django Posts CRUD application.
Tests all endpoints: list, create, update, delete.
"""
from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import random
import string
import os

# Import metrics collector if available
try:
    from locust_metrics_collector import init_metrics_collector
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    print("Metrics collector not available. Install psutil for memory tracking: pip install psutil")


class PostsUser(HttpUser):
    """Simulates a user interacting with the Posts CRUD application."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts. Get CSRF token."""
        # Get CSRF token from the list page
        response = self.client.get("/posts/")
        if response.status_code == 200:
            # Extract CSRF token from the page
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_token:
                self.csrf_token = csrf_token.get('value')
            else:
                # Try to get from cookies
                self.csrf_token = response.cookies.get('csrftoken', '')
        else:
            self.csrf_token = ''
        
        # Store created post IDs for update/delete operations
        self.created_post_ids = []
    
    def get_csrf_token(self, response):
        """Extract CSRF token from response."""
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            return csrf_input.get('value')
        return response.cookies.get('csrftoken', '')
    
    def generate_random_string(self, length=10):
        """Generate random string for test data."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @task(3)
    def view_post_list(self):
        """View the list of all posts (most common operation)."""
        with self.client.get("/posts/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load post list: {response.status_code}")
    
    @task(2)
    def create_post(self):
        """Create a new post."""
        # First, get the create form to obtain CSRF token
        form_response = self.client.get("/posts/create/")
        csrf_token = self.get_csrf_token(form_response)
        
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')
        
        # Generate random test data
        title = f"Test Post {self.generate_random_string(8)}"
        author = f"Author {self.generate_random_string(6)}"
        
        # Create the post
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
            if response.status_code in [200, 302]:  # 302 is redirect after successful creation
                response.success()
                # Try to extract the created post ID from redirect or response
                # For now, we'll track that a post was created
            else:
                response.failure(f"Failed to create post: {response.status_code}")
    
    @task(1)
    def update_post(self):
        """Update an existing post."""
        # First, get the list to find existing posts
        list_response = self.client.get("/posts/")
        if list_response.status_code != 200:
            return
        
        # Parse the HTML to find post IDs (this is a simplified approach)
        # In a real scenario, you might want to track created posts
        soup = BeautifulSoup(list_response.text, 'html.parser')
        update_links = soup.find_all('a', href=lambda x: x and '/posts/update/' in x)
        
        if not update_links:
            # No posts to update, skip this task
            return
        
        # Get the first update link
        update_url = update_links[0].get('href')
        post_id = update_url.split('/')[-2] if update_url else None
        
        if not post_id:
            return
        
        # Get the update form
        form_response = self.client.get(f"/posts/update/{post_id}/")
        csrf_token = self.get_csrf_token(form_response)
        
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')
        
        # Update the post with new data
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
        """Delete a post."""
        # First, get the list to find existing posts
        list_response = self.client.get("/posts/")
        if list_response.status_code != 200:
            return
        
        # Parse the HTML to find delete links
        soup = BeautifulSoup(list_response.text, 'html.parser')
        delete_links = soup.find_all('a', href=lambda x: x and '/posts/delete/' in x)
        
        if not delete_links:
            # No posts to delete, skip this task
            return
        
        # Get the first delete link
        delete_url = delete_links[0].get('href')
        post_id = delete_url.split('/')[-2] if delete_url else None
        
        if not post_id:
            return
        
        # Get the delete confirmation page
        form_response = self.client.get(f"/posts/delete/{post_id}/")
        csrf_token = self.get_csrf_token(form_response)
        
        if not csrf_token:
            csrf_token = form_response.cookies.get('csrftoken', '')
        
        # Confirm deletion
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


# Initialize metrics collector when Locust starts
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collector when Locust starts."""
    if METRICS_ENABLED:
        # Try to find Django PID or set to None to auto-detect
        django_pid = os.environ.get('DJANGO_PID', None)
        if django_pid:
            django_pid = int(django_pid)
        
        output_dir = os.environ.get('LOCUST_METRICS_DIR', 'results')
        init_metrics_collector(django_pid=django_pid, output_dir=output_dir, environment=environment)
        print("✓ Memory and scalability metrics collector initialized")

