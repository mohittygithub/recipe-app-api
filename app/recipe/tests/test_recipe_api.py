"""Tests for reicpe api's"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPES_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    """Create and return a recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """Create and return a recipe"""
    defaults = {
        'title':'Sample Recipe',
        'time_minutes':5,
        'price':Decimal('5.50'),
        'description':'Sample Recipe description',
        'link':'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
    """Create and return new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call the API"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='test@example.com', password='Test@1234')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes limited to the authenticated users"""
        other_user = create_user(email='other@example.com', password='Other@1234')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title':'Sample Recipe',
            'time_minutes':5,
            'price':Decimal('5.50'),
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test patial update of a recipe"""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(user=self.user, title='sample recipe title', link=original_link)

        payload = {'title': 'new recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe"""
        recipe = create_recipe(
            user=self.user,
            title='sample recipe title',
            link='https://example.com/recipe.pdf',
            description='sample recipe description',
        )

        payload = {
            'title':'New Recipe',
            'time_minutes':5,
            'price':Decimal('5.50'),
            'description':'New Recipe description',
            'link':'http://example.com/new-recipe.pdf',
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error"""
        new_user = create_user(email='user@example.com', password='User@1234')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_user_recipe(self):
        """Test trying to delete othere user's recipe gives error"""
        new_user = create_user(email='newuser@example.com', password='User@1234')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

