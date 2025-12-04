"""
Database models for email redirect tool
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = None):
        # Use provided path or default to current directory
        if db_path:
            self.db_path = db_path
        else:
            import os
            # Use environment variable if available (for production)
            self.db_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

        print(f"Using database at: {self.db_path}")
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

            # Add dns_issues column if it doesn't exist (for DNS validation)
            try:
                cursor.execute('ALTER TABLE domains ADD COLUMN dns_issues TEXT')
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
            
            # DNS records table for complete DNS backup and restore
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dns_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_name TEXT NOT NULL,
                    record_name TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    record_address TEXT NOT NULL,
                    ttl TEXT,
                    mx_pref TEXT,
                    backup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_current BOOLEAN DEFAULT TRUE,
                    is_url_redirect BOOLEAN DEFAULT FALSE,
                    UNIQUE(domain_name, record_name, record_type, is_current)
                )
            ''')

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
                
                # Use INSERT OR IGNORE to handle race conditions
                cursor.execute('''
                    INSERT OR IGNORE INTO domains (domain_number, domain_name, client_id)
                    VALUES (?, ?, ?)
                ''', (domain_number, domain_name, client_id))

                # If it was ignored (already exists), get the existing one
                if cursor.rowcount == 0:
                    cursor.execute('SELECT id, domain_number FROM domains WHERE domain_name = ?', (domain_name,))
                    existing = cursor.fetchone()
                    if existing:
                        return existing[1]
                
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
                    d.updated_at, d.sync_status, d.dns_issues
                FROM domains d
                LEFT JOIN clients c ON d.client_id = c.id
                ORDER BY d.domain_number
            ''')

            domains = []
            for row in cursor.fetchall():
                domain_id, domain_number, domain_name, client_name, client_id, updated_at, sync_status, dns_issues = row
                
                # Get redirections
                cursor.execute('''
                    SELECT redirect_name, redirect_target, redirect_type
                    FROM redirections WHERE domain_id = ?
                ''', (domain_id,))

                redirections = []
                auto_detected_client_id = client_id
                auto_detected_client_name = client_name

                for redirect_row in cursor.fetchall():
                    redirections.append({
                        'name': redirect_row[0],
                        'target': redirect_row[1],
                        'type': redirect_row[2]
                    })

                    # Auto-detect client from redirect URL if not already assigned
                    if not client_id or client_name == 'Unassigned':
                        redirect_target = redirect_row[1]
                        if redirect_target:
                            matched_client = self.find_client_by_url(redirect_target)
                            if matched_client:
                                auto_detected_client_id = matched_client['id']
                                auto_detected_client_name = matched_client['name']
                                # Update domain with detected client
                                cursor.execute('''
                                    UPDATE domains SET client_id = ? WHERE id = ?
                                ''', (matched_client['id'], domain_id))

                domains.append({
                    'id': domain_id,
                    'domain_number': domain_number,
                    'domain_name': domain_name,
                    'client_name': auto_detected_client_name or 'Unassigned',
                    'client_id': auto_detected_client_id,
                    'redirections': redirections,
                    'updated_at': updated_at,
                    'sync_status': sync_status or 'unchanged',
                    'dns_issues': dns_issues
                })
            
            return domains
    
    def get_all_clients(self) -> List[Dict]:
        """Get all clients"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, client_name, client_url FROM clients ORDER BY client_name')

            return [{'id': row[0], 'name': row[1], 'url': row[2]} for row in cursor.fetchall()]

    def find_client_by_url(self, url: str) -> Optional[Dict]:
        """Find client by URL"""
        if not url or not url.strip():
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, client_name, client_url FROM clients WHERE client_url = ?', (url.strip(),))
            result = cursor.fetchone()

            if result:
                return {
                    'id': result[0],
                    'name': result[1],
                    'url': result[2]
                }
            return None
    
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

    def update_client(self, client_id: int, client_name: str, client_url: str):
        """Update client name and URL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE clients SET client_name = ?, client_url = ? WHERE id = ?', (client_name, client_url, client_id))
    
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

    def update_domain_dns_issues(self, domain_name: str, issues: str):
        """Update DNS issues for a domain"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # First check if domain exists
            cursor.execute('SELECT id FROM domains WHERE domain_name = ?', (domain_name,))
            domain_exists = cursor.fetchone()

            if domain_exists:
                # Update existing domain
                cursor.execute('''
                    UPDATE domains SET dns_issues = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE domain_name = ?
                ''', (issues, domain_name))
            else:
                # Insert new domain with dns_issues
                # Get next domain number
                cursor.execute('SELECT MAX(domain_number) FROM domains')
                max_num = cursor.fetchone()[0]
                next_num = (max_num or 0) + 1

                # Get "Unassigned" client ID
                cursor.execute('SELECT id FROM clients WHERE client_name = ?', ('Unassigned',))
                unassigned_client = cursor.fetchone()
                client_id = unassigned_client[0] if unassigned_client else None

                cursor.execute('''
                    INSERT INTO domains (domain_number, domain_name, client_id, dns_issues, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (next_num, domain_name, client_id, issues))

            conn.commit()

    def check_dns_records_for_domain(self, domain_name: str) -> str:
        """
        Check stored DNS records for a domain and return issues or 'ok'

        Checks for:
        - SPF: TXT record containing "v=spf1"
        - Google verification: TXT record containing "google-site-verification"
        - DMARC: Record with hostname "_dmarc"
        - DKIM: Record containing "v=DKIM1;"

        Returns:
            'ok' if all records found, otherwise string describing missing records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get current DNS records for this domain
            cursor.execute('''
                SELECT record_name, record_type, record_address
                FROM dns_records
                WHERE domain_name = ? AND is_current = TRUE
            ''', (domain_name,))

            dns_records = cursor.fetchall()

            if not dns_records:
                # sync from api

                return None

            # Track found records
            spf_found = False
            google_verification_found = False
            dmarc_found = False
            dkim_found = False
            print('=' * 20)
            print(dns_records)
            print('=' * 20)
            # Check each stored DNS record
            for record_name, record_type, record_address in dns_records:
                record_type = record_type.upper()
                record_name = record_name.lower()
                record_address = record_address.strip()

                # Check SPF record (TXT record containing "v=spf1")
                if 'v=spf1' in record_address:
                    spf_found = True

                # Check Google verification (TXT record containing "google-site-verification")
                if 'google-site-verification' in record_address:
                    google_verification_found = True

                # Check DMARC record (hostname "_dmarc")
                if record_name == '_dmarc':
                    dmarc_found = True

                # Check DKIM record (any record containing "v=DKIM1;")
                if 'v=DKIM1;' in record_address:
                    dkim_found = True

            # Build list of missing records
            missing_records = []
            if not spf_found:
                missing_records.append('SPF')
            if not google_verification_found:
                missing_records.append('Google Verification')
            if not dmarc_found:
                missing_records.append('DMARC')
            if not dkim_found:
                missing_records.append('DKIM')

            if missing_records:
                return f"Missing: {', '.join(missing_records)}"
            else:
                return 'ok'

    # DNS Backup and Restore Methods
    def backup_dns_records(self, domain_name: str, dns_records: List[Dict]) -> bool:
        """
        Backup complete DNS records for a domain before making changes

        Args:
            domain_name: The domain to backup
            dns_records: List of DNS records from Namecheap API

        Returns:
            bool: True if backup successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Mark previous records as not current
                cursor.execute('''
                    UPDATE dns_records SET is_current = FALSE
                    WHERE domain_name = ? AND is_current = TRUE
                ''', (domain_name,))

                # Insert current DNS records
                for record in dns_records:
                    is_url_redirect = record.get('Type', '').upper() == 'URL'

                    cursor.execute('''
                        INSERT OR REPLACE INTO dns_records
                        (domain_name, record_name, record_type, record_address, ttl, mx_pref, is_url_redirect, is_current)
                        VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
                    ''', (
                        domain_name,
                        record.get('Name', '@'),
                        record.get('Type', ''),
                        record.get('Address', ''),
                        record.get('TTL', ''),
                        record.get('MXPref', ''),
                        is_url_redirect
                    ))

                conn.commit()
                print(f"✅ Backed up {len(dns_records)} DNS records for {domain_name}")
                return True

        except Exception as e:
            print(f"❌ Failed to backup DNS records for {domain_name}: {e}")
            return False

    def get_current_dns_records(self, domain_name: str) -> List[Dict]:
        """
        Get current DNS records for a domain from backup

        Args:
            domain_name: The domain to get records for

        Returns:
            List[Dict]: Current DNS records in Namecheap API format
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT record_name, record_type, record_address, ttl, mx_pref, is_url_redirect
                FROM dns_records
                WHERE domain_name = ? AND is_current = TRUE
                ORDER BY record_type, record_name
            ''', (domain_name,))

            records = []
            for row in cursor.fetchall():
                record = {
                    'Name': row[0],
                    'Type': row[1],
                    'Address': row[2],
                    'TTL': row[3] or '1800'
                }

                # Add MXPref for MX records
                if row[1].upper() == 'MX' and row[4]:
                    record['MXPref'] = row[4]

                records.append(record)

            return records

    def update_redirect_in_backup(self, domain_name: str, redirect_name: str, new_target: str) -> List[Dict]:
        """
        Update a URL redirect in the DNS backup and return complete record set
        This also removes any existing parking page records (CNAME, A records) for the same name

        Args:
            domain_name: The domain to update
            redirect_name: The redirect name (e.g., '@', 'www')
            new_target: The new redirect target URL

        Returns:
            List[Dict]: Complete DNS records with updated redirect
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # STEP 1: Remove any existing parking page records for this name
            # This includes CNAME records pointing to parking services like parkingpage.namecheap.com
            parking_indicators = [
                'parkingpage.namecheap.com', 'parking', 'namecheap'
            ]

            # Delete any records for this name that might be parking pages
            cursor.execute('''
                DELETE FROM dns_records
                WHERE domain_name = ? AND record_name = ? AND is_current = TRUE
                AND (record_type IN ('CNAME', 'A') OR record_address LIKE '%parking%' OR record_address LIKE '%parkingpage.namecheap.com%')
            ''', (domain_name, redirect_name))

            removed_count = cursor.rowcount
            if removed_count > 0:
                print(f"🗑️  Removed {removed_count} parking page record(s) for {redirect_name}")

            # STEP 2: Update existing URL redirect record if it exists
            cursor.execute('''
                UPDATE dns_records
                SET record_address = ?, backup_timestamp = CURRENT_TIMESTAMP
                WHERE domain_name = ? AND record_name = ? AND record_type = 'URL' AND is_current = TRUE
            ''', (new_target, domain_name, redirect_name))

            # STEP 3: If no URL redirect was updated, insert new redirect
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO dns_records
                    (domain_name, record_name, record_type, record_address, ttl, is_url_redirect, is_current)
                    VALUES (?, ?, 'URL', ?, '300', TRUE, TRUE)
                ''', (domain_name, redirect_name, new_target))
                print(f"➕ Added new URL redirect: {redirect_name} -> {new_target}")
            else:
                print(f"✏️  Updated URL redirect: {redirect_name} -> {new_target}")

            conn.commit()

        # Return complete updated record set
        return self.get_current_dns_records(domain_name)

    def get_dns_backup_history(self, domain_name: str, limit: int = 10) -> List[Dict]:
        """
        Get DNS backup history for a domain

        Args:
            domain_name: The domain to get history for
            limit: Maximum number of backups to return

        Returns:
            List[Dict]: DNS backup history
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT backup_timestamp, COUNT(*) as record_count
                FROM dns_records
                WHERE domain_name = ?
                GROUP BY backup_timestamp
                ORDER BY backup_timestamp DESC
                LIMIT ?
            ''', (domain_name, limit))

            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row[0],
                    'record_count': row[1]
                })

            return history