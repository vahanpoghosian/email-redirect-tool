"""
Database models for email redirect tool
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = 'redirect_tool.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Domains table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_number INTEGER UNIQUE NOT NULL,
                    domain_name TEXT UNIQUE NOT NULL,
                    client_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            ''')
            
            # Redirections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS redirections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_id INTEGER NOT NULL,
                    redirect_name TEXT NOT NULL,
                    redirect_target TEXT NOT NULL,
                    redirect_type TEXT DEFAULT 'URL',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (domain_id) REFERENCES domains (id)
                )
            ''')
            
            # Clients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT UNIQUE NOT NULL,
                    client_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add client_url column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE clients ADD COLUMN client_url TEXT')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add sync_status column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE domains ADD COLUMN sync_status TEXT DEFAULT "unchanged"')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Users table for authentication
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create default user
            self._create_default_user(cursor)
            
            # Create default "Unassigned" client
            cursor.execute('''
                INSERT OR IGNORE INTO clients (client_name) VALUES ('Unassigned')
            ''')
            
            conn.commit()
    
    def _create_default_user(self, cursor):
        """Create default user with specified credentials"""
        username = 'vahanpoghosian'
        password = 'JPqW*yI7iem'
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)
        ''', (username, password_hash))
    
    def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM users WHERE username = ? AND password_hash = ?
            ''', (username, password_hash))
            
            return cursor.fetchone() is not None
    
    def get_next_domain_number(self) -> int:
        """Get the next available domain number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(domain_number) FROM domains')
            result = cursor.fetchone()
            
            if result[0] is None:
                return 1
            else:
                return result[0] + 1
    
    def add_or_update_domain(self, domain_name: str, client_id: Optional[int] = None) -> int:
        """Add new domain or update existing one, return domain_number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if domain exists
            cursor.execute('SELECT id, domain_number FROM domains WHERE domain_name = ?', (domain_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update timestamp
                cursor.execute('''
                    UPDATE domains SET updated_at = CURRENT_TIMESTAMP 
                    WHERE domain_name = ?
                ''', (domain_name,))
                return existing[1]  # Return existing domain_number
            else:
                # Add new domain
                domain_number = self.get_next_domain_number()
                
                if client_id is None:
                    # Get "Unassigned" client ID
                    cursor.execute('SELECT id FROM clients WHERE client_name = ?', ('Unassigned',))
                    client_id = cursor.fetchone()[0]
                
                cursor.execute('''
                    INSERT INTO domains (domain_number, domain_name, client_id)
                    VALUES (?, ?, ?)
                ''', (domain_number, domain_name, client_id))
                
                return domain_number
    
    def get_domain_id(self, domain_name: str) -> Optional[int]:
        """Get domain ID by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM domains WHERE domain_name = ?', (domain_name,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def update_redirections(self, domain_name: str, redirections: List[Dict]):
        """Update redirections for a domain"""
        domain_id = self.get_domain_id(domain_name)
        if not domain_id:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing redirections
            cursor.execute('DELETE FROM redirections WHERE domain_id = ?', (domain_id,))
            
            # Add new redirections
            for redirect in redirections:
                cursor.execute('''
                    INSERT INTO redirections (domain_id, redirect_name, redirect_target, redirect_type)
                    VALUES (?, ?, ?, ?)
                ''', (domain_id, redirect.get('name', '@'), redirect.get('target', ''), redirect.get('type', 'URL')))
    
    def get_all_domains_with_redirections(self) -> List[Dict]:
        """Get all domains with their redirections and client info"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    d.id, d.domain_number, d.domain_name, 
                    c.client_name, c.id as client_id,
                    d.updated_at, d.sync_status
                FROM domains d
                LEFT JOIN clients c ON d.client_id = c.id
                ORDER BY d.domain_number
            ''')
            
            domains = []
            for row in cursor.fetchall():
                domain_id, domain_number, domain_name, client_name, client_id, updated_at, sync_status = row
                
                # Get redirections
                cursor.execute('''
                    SELECT redirect_name, redirect_target, redirect_type
                    FROM redirections WHERE domain_id = ?
                ''', (domain_id,))
                
                redirections = []
                for redirect_row in cursor.fetchall():
                    redirections.append({
                        'name': redirect_row[0],
                        'target': redirect_row[1],
                        'type': redirect_row[2]
                    })
                
                domains.append({
                    'id': domain_id,
                    'domain_number': domain_number,
                    'domain_name': domain_name,
                    'client_name': client_name or 'Unassigned',
                    'client_id': client_id,
                    'redirections': redirections,
                    'updated_at': updated_at,
                    'sync_status': sync_status or 'unchanged'
                })
            
            return domains
    
    def get_all_clients(self) -> List[Dict]:
        """Get all clients"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, client_name, client_url FROM clients ORDER BY client_name')
            
            return [{'id': row[0], 'name': row[1], 'url': row[2]} for row in cursor.fetchall()]
    
    def add_client(self, client_name: str, client_url: str = None) -> int:
        """Add new client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO clients (client_name, client_url) VALUES (?, ?)', (client_name, client_url))
            return cursor.lastrowid
    
    def update_client_url(self, client_id: int, client_url: str):
        """Update client URL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE clients SET client_url = ? WHERE id = ?', (client_url, client_id))
    
    def delete_client(self, client_id: int):
        """Delete client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # First, set all domains using this client to "Unassigned"
            unassigned_client_id = self.get_unassigned_client_id()
            cursor.execute('UPDATE domains SET client_id = ? WHERE client_id = ?', (unassigned_client_id, client_id))
            # Then delete the client
            cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    
    def get_unassigned_client_id(self) -> int:
        """Get the ID of the 'Unassigned' client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM clients WHERE client_name = ?', ('Unassigned',))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def assign_domain_to_client(self, domain_name: str, client_id: int):
        """Assign domain to client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE domains SET client_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE domain_name = ?
            ''', (client_id, domain_name))
    
    def update_domain_sync_status(self, domain_name: str, status: str):
        """Update sync status for a domain"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE domains SET sync_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE domain_name = ?
            ''', (status, domain_name))