"""Generate embeddings for text and visual content."""

from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2


class Embedder:
    """Generates embeddings for multimodal content."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_model_name = config['embeddings']['text_model']
        self.visual_model_name = config['embeddings']['visual_model']
        self.batch_size = config['embeddings']['batch_size']
        
        self.text_model = None
        self.visual_model = None
        self.visual_processor = None
    
    def _load_text_model(self):
        """Lazy load text embedding model."""
        if self.text_model is None:
            print(f"Loading text embedding model: {self.text_model_name}")
            self.text_model = SentenceTransformer(self.text_model_name)
    
    def _load_visual_model(self):
        """Lazy load visual embedding model."""
        if self.visual_model is None:
            print(f"Loading visual embedding model: {self.visual_model_name}")
            self.visual_model = CLIPModel.from_pretrained(self.visual_model_name)
            self.visual_processor = CLIPProcessor.from_pretrained(self.visual_model_name)
            self.visual_model.eval()
    
    def embed_text(self, texts: List[str]) -> np.ndarray:
        """
        Generate text embeddings.
        
        Args:
            texts: List of text strings
        
        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])
        
        self._load_text_model()
        
        # Filter empty texts
        valid_texts = [t if t else " " for t in texts]
        
        # Generate embeddings in batches
        embeddings = self.text_model.encode(
            valid_texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def embed_image(self, image_path: Path) -> np.ndarray:
        """
        Generate visual embedding for a single image.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        self._load_visual_model()
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        
        # Process image
        inputs = self.visual_processor(images=image, return_tensors="pt")
        
        # Generate embedding
        with torch.no_grad():
            image_features = self.visual_model.get_image_features(**inputs)
            # Normalize
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        return image_features.cpu().numpy().flatten()
    
    def embed_images_batch(self, image_paths: List[Path]) -> np.ndarray:
        """
        Generate visual embeddings for multiple images.
        
        Args:
            image_paths: List of image paths
        
        Returns:
            Numpy array of shape (len(image_paths), embedding_dim)
        """
        if not image_paths:
            return np.array([])
        
        self._load_visual_model()
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i:i + self.batch_size]
            
            # Load images
            images = []
            for path in batch_paths:
                try:
                    img = Image.open(path).convert('RGB')
                    images.append(img)
                except Exception as e:
                    print(f"Error loading image {path}: {e}")
                    # Use blank image as fallback
                    images.append(Image.new('RGB', (224, 224), color='black'))
            
            # Process batch
            inputs = self.visual_processor(images=images, return_tensors="pt")
            
            # Generate embeddings
            with torch.no_grad():
                image_features = self.visual_model.get_image_features(**inputs)
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            embeddings.append(image_features.cpu().numpy())
        
        return np.vstack(embeddings)
    
    def detect_faces(self, image_path: Path) -> bool:
        """
        Simple face detection using OpenCV Haar Cascade.
        
        Returns:
            True if faces detected, False otherwise
        """
        # Load cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            return False
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return len(faces) > 0
    
    def get_embedding_dimensions(self) -> Dict[str, int]:
        """Get dimensions of embeddings."""
        self._load_text_model()
        self._load_visual_model()
        
        return {
            'text': self.text_model.get_sentence_embedding_dimension(),
            'visual': self.visual_model.config.projection_dim
        }
