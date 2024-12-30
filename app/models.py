import os
import time
import uuid
import boto3
from pydantic import BaseModel, Field
from typing import List, Optional

TABLE_NAME = os.getenv('TABLE_NAME')

# Define request and response models
class QueryRequest(BaseModel):
    query_text: str


class QueryResult(BaseModel):
    query_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    create_time: int = Field(default_factory=lambda: int(time.time()))
    query_text: str
    answer_text: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    is_complete: bool = False

    
    @classmethod
    def get_table(cls):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        return table
    
    def to_dict(self):
        # This will work with both v1 and v2
        try:
            return self.model_dump()
        except AttributeError:
            return self.dict()
    
    def get_items(self):
        return {
            'query_id': self.query_id,
            'create_time': self.create_time,
            'query_text': self.query_text,
            'answer_text': self.answer_text,
            'sources': self.sources,
            'is_complete': self.is_complete
        }



    def put_item_into_table(self):
        table = self.get_table()
        item = self.get_items()

        try:
            table.put_item(Item=item)
            print('Successfully put item into table.')
        except Exception as e:
            print(f"Failed to put item into table: {e}")
            return False
        
        return True
    

    @classmethod
    def get_item_from_table(cls, query_id):
        table = cls.get_table()
        
        try:
            response = table.get_item(Key={'query_id': query_id})

        except Exception as e:
            print(f"Failed to get item from table: {e}")
            return None
        
        if 'Item' not in response:
            return None
        

        else:
            item = response['Item']
            return cls(**item)

                                           