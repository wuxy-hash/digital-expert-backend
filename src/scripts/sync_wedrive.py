#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.knowledge.sync import sync_knowledge_from_wedrive

if __name__ == "__main__":
    sync_knowledge_from_wedrive()