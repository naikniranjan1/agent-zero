#!/usr/bin/env python3
"""
Create MongoDB Atlas Vector Search Index via API
This script automates the creation of the vector search index
"""

import os
import sys
import json
import requests
import base64
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.print_style import PrintStyle

# Load environment variables
load_dotenv()


class AtlasVectorIndexCreator:
    """Create Atlas Vector Search Index via API"""
    
    def __init__(self):
        self.api_public_key = os.getenv("MONGODB_ATLAS_PUBLIC_KEY")
        self.api_private_key = os.getenv("MONGODB_ATLAS_PRIVATE_KEY")
        self.project_id = os.getenv("MONGODB_ATLAS_PROJECT_ID")
        self.cluster_name = os.getenv("MONGODB_ATLAS_CLUSTER_NAME", "Cluster0")
        self.database_name = os.getenv("MONGODB_DATABASE", "agent_zero")
        
        # Vector search index configuration
        self.index_config = {
            "name": "vector_search_index",
            "database": self.database_name,
            "collectionName": "user_memory",
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 1536,
                        "similarity": "cosine"
                    },
                    {
                        "type": "filter",
                        "path": "user_id"
                    },
                    {
                        "type": "filter",
                        "path": "metadata.timestamp"
                    },
                    {
                        "type": "filter",
                        "path": "metadata.area"
                    },
                    {
                        "type": "filter",
                        "path": "metadata.type"
                    }
                ]
            }
        }
    
    def check_credentials(self) -> bool:
        """Check if Atlas API credentials are available"""
        if not all([self.api_public_key, self.api_private_key, self.project_id]):
            PrintStyle.error("❌ MongoDB Atlas API credentials not found")
            PrintStyle.hint("\nTo get your Atlas API credentials:")
            PrintStyle.hint("1. Go to MongoDB Atlas Dashboard")
            PrintStyle.hint("2. Click on 'Access Manager' in the left sidebar")
            PrintStyle.hint("3. Go to 'API Keys' tab")
            PrintStyle.hint("4. Click 'Create API Key'")
            PrintStyle.hint("5. Set permissions to 'Project Owner'")
            PrintStyle.hint("6. Copy the Public Key and Private Key")
            PrintStyle.hint("7. Add them to your .env file:")
            PrintStyle.hint("   MONGODB_ATLAS_PUBLIC_KEY=your_public_key")
            PrintStyle.hint("   MONGODB_ATLAS_PRIVATE_KEY=your_private_key")
            PrintStyle.hint("   MONGODB_ATLAS_PROJECT_ID=your_project_id")
            PrintStyle.hint("\nTo find your Project ID:")
            PrintStyle.hint("1. Go to MongoDB Atlas Dashboard")
            PrintStyle.hint("2. Click on 'Project Settings' in the left sidebar")
            PrintStyle.hint("3. Copy the 'Project ID'")
            return False
        
        PrintStyle.success("✅ Atlas API credentials found")
        return True
    
    def create_vector_index(self) -> bool:
        """Create the vector search index via Atlas API"""
        try:
            PrintStyle.standard("Creating vector search index via Atlas API...")
            
            # Create authentication header
            credentials = f"{self.api_public_key}:{self.api_private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Atlas API endpoint for search indexes
            url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{self.project_id}/clusters/{self.cluster_name}/search/indexes"
            
            PrintStyle.standard(f"API Endpoint: {url}")
            PrintStyle.standard(f"Project ID: {self.project_id}")
            PrintStyle.standard(f"Cluster: {self.cluster_name}")
            PrintStyle.standard(f"Database: {self.database_name}")
            PrintStyle.standard(f"Collection: {self.index_config['collectionName']}")
            
            # Make API request
            response = requests.post(
                url, 
                json=self.index_config, 
                headers=headers, 
                timeout=30
            )
            
            if response.status_code == 201:
                PrintStyle.success("✅ Vector search index created successfully!")
                response_data = response.json()
                PrintStyle.success(f"Index ID: {response_data.get('indexID', 'N/A')}")
                PrintStyle.success(f"Index Name: {response_data.get('name', 'N/A')}")
                PrintStyle.success(f"Status: {response_data.get('status', 'N/A')}")
                return True
                
            elif response.status_code == 409:
                PrintStyle.success("✅ Vector search index already exists!")
                return True
                
            elif response.status_code == 401:
                PrintStyle.error("❌ Authentication failed - check your API credentials")
                return False
                
            elif response.status_code == 403:
                PrintStyle.error("❌ Permission denied - check your API key permissions")
                PrintStyle.hint("Make sure your API key has 'Project Owner' permissions")
                return False
                
            else:
                PrintStyle.error(f"❌ API request failed: {response.status_code}")
                try:
                    error_data = response.json()
                    PrintStyle.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    PrintStyle.error(f"Response text: {response.text}")
                return False
            
        except requests.exceptions.Timeout:
            PrintStyle.error("❌ Request timeout - please try again")
            return False
        except requests.exceptions.ConnectionError:
            PrintStyle.error("❌ Connection error - check your internet connection")
            return False
        except Exception as e:
            PrintStyle.error(f"❌ Unexpected error: {str(e)}")
            return False
    
    def verify_index(self) -> bool:
        """Verify the vector search index was created"""
        try:
            PrintStyle.standard("Verifying vector search index...")
            
            # Create authentication header
            credentials = f"{self.api_public_key}:{self.api_private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "application/json"
            }
            
            # Get all search indexes
            url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{self.project_id}/clusters/{self.cluster_name}/search/indexes"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                indexes = response.json()
                
                # Look for our vector index
                for index in indexes:
                    if (index.get("name") == self.index_config["name"] and 
                        index.get("database") == self.database_name and
                        index.get("collectionName") == self.index_config["collectionName"]):
                        
                        PrintStyle.success("✅ Vector search index verified!")
                        PrintStyle.success(f"Index ID: {index.get('indexID')}")
                        PrintStyle.success(f"Status: {index.get('status')}")
                        
                        if index.get('status') == 'IN_PROGRESS':
                            PrintStyle.hint("⏳ Index is still building - this may take a few minutes")
                        elif index.get('status') == 'READY':
                            PrintStyle.success("🎉 Index is ready for use!")
                        
                        return True
                
                PrintStyle.warning("⚠ Vector search index not found")
                return False
            else:
                PrintStyle.error(f"❌ Failed to verify index: {response.status_code}")
                return False
                
        except Exception as e:
            PrintStyle.error(f"❌ Verification failed: {str(e)}")
            return False
    
    def show_manual_instructions(self):
        """Show manual creation instructions"""
        PrintStyle.standard("\n" + "="*60)
        PrintStyle.warning("📋 MANUAL VECTOR INDEX CREATION")
        PrintStyle.standard("="*60)
        
        PrintStyle.hint("\n1. Go to MongoDB Atlas Dashboard")
        PrintStyle.hint("2. Navigate to Database → Search")
        PrintStyle.hint("3. Click 'Create Search Index'")
        PrintStyle.hint("4. Select 'Atlas Vector Search'")
        PrintStyle.hint("5. Use these settings:")
        PrintStyle.hint(f"   • Database: {self.database_name}")
        PrintStyle.hint(f"   • Collection: {self.index_config['collectionName']}")
        PrintStyle.hint(f"   • Index Name: {self.index_config['name']}")
        
        PrintStyle.hint("\n6. Use this JSON configuration:")
        print(json.dumps(self.index_config["definition"], indent=2))


def main():
    """Main function"""
    PrintStyle.standard("🔍 MongoDB Atlas Vector Search Index Creator")
    PrintStyle.standard("="*60)
    
    creator = AtlasVectorIndexCreator()
    
    # Check credentials
    if not creator.check_credentials():
        creator.show_manual_instructions()
        return False
    
    # Create vector index
    if creator.create_vector_index():
        # Verify creation
        creator.verify_index()
        
        PrintStyle.success("\n🎉 Vector Search Index Setup Complete!")
        PrintStyle.hint("Agent Zero is now ready for full MongoDB Atlas operation")
        return True
    else:
        PrintStyle.error("\n❌ Failed to create vector search index")
        creator.show_manual_instructions()
        return False


if __name__ == "__main__":
    success = main()
    
    if success:
        PrintStyle.success("\n✅ All done! You can now use Agent Zero with MongoDB Atlas")
    else:
        PrintStyle.hint("\n💡 You can still use Agent Zero - just create the index manually")
