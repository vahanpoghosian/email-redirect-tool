"""
Namecheap Email Redirection Client
Handles API communication with Namecheap for bulk email forwarding
"""

import requests
import json
import csv
import os
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

class NamecheapAPIError(Exception):
    """Custom exception for Namecheap API errors"""
    pass

class RateLimitState:
    """Thread-safe rate limiting state tracker"""

    def __init__(self):
        self.lock = threading.Lock()
        self.request_timestamps = []
        self.is_paused = False
        self.pause_until = None
        self.pause_reason = None
        self.requests_per_minute = 20
        self.requests_per_hour = 700
        self.requests_per_day = 8000
        self.min_delay_between_requests = 3.0

    def record_request(self):
        """Record a request timestamp"""
        with self.lock:
            now = time.time()
            self.request_timestamps.append(now)
            one_day_ago = now - 86400
            self.request_timestamps = [ts for ts in self.request_timestamps if ts > one_day_ago]

    def _get_counts_unlocked(self):
        """Get request counts (must be called with lock held)"""
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        one_day_ago = now - 86400

        minute_count = sum(1 for ts in self.request_timestamps if ts > one_minute_ago)
        hour_count = sum(1 for ts in self.request_timestamps if ts > one_hour_ago)
        day_count = sum(1 for ts in self.request_timestamps if ts > one_day_ago)

        return minute_count, hour_count, day_count

    def get_counts(self):
        """Get request counts for last minute, hour, and day"""
        with self.lock:
            return self._get_counts_unlocked()

    def should_wait(self):
        """Check if we should wait before making a request, returns wait time in seconds"""
        with self.lock:
            if self.is_paused:
                if self.pause_until and time.time() < self.pause_until:
                    return self.pause_until - time.time()
                else:
                    self.is_paused = False
                    self.pause_until = None
                    self.pause_reason = None

            minute_count, hour_count, day_count = self._get_counts_unlocked()
            now = time.time()

            if minute_count >= self.requests_per_minute - 1 and len(self.request_timestamps) >= self.requests_per_minute:
                return max(0, 60 - (now - self.request_timestamps[-self.requests_per_minute]))
            if hour_count >= self.requests_per_hour - 10 and len(self.request_timestamps) >= self.requests_per_hour:
                return max(0, 3600 - (now - self.request_timestamps[-self.requests_per_hour]))
            if day_count >= self.requests_per_day - 100 and len(self.request_timestamps) >= self.requests_per_day:
                return max(0, 86400 - (now - self.request_timestamps[-self.requests_per_day]))

            return 0

    def set_paused(self, duration_seconds=900, reason="Rate limit exceeded"):
        """Pause requests for specified duration (default 15 minutes)"""
        with self.lock:
            self.is_paused = True
            self.pause_until = time.time() + duration_seconds
            self.pause_reason = reason

    def resume(self):
        """Resume requests"""
        with self.lock:
            self.is_paused = False
            self.pause_until = None
            self.pause_reason = None

    def get_status(self):
        """Get current rate limit status"""
        with self.lock:
            minute_count, hour_count, day_count = self._get_counts_unlocked()
            return {
                "is_paused": self.is_paused,
                "pause_until": self.pause_until,
                "pause_reason": self.pause_reason,
                "time_until_resume": max(0, self.pause_until - time.time()) if self.pause_until else 0,
                "requests_last_minute": minute_count,
                "requests_last_hour": hour_count,
                "requests_last_day": day_count,
                "limits": {
                    "per_minute": self.requests_per_minute,
                    "per_hour": self.requests_per_hour,
                    "per_day": self.requests_per_day
                }
            }

rate_limit_state = RateLimitState()

class NamecheapAPIClient:
    """Client for Namecheap API operations"""

    def __init__(self):
        """Initialize Namecheap API client"""
        self.base_url = "https://api.namecheap.com/xml.response"
        self.rate_limit = rate_limit_state
        self.api_user = os.environ.get('NAMECHEAP_API_USER')
        self.api_key = os.environ.get('NAMECHEAP_API_KEY')
        self.username = os.environ.get('NAMECHEAP_USERNAME', self.api_user)
        
        # Auto-detect our outbound IP with fallback to configured one
        self.client_ip = self._detect_outbound_ip()

        print(f"Namecheap API Client initialized:")
        print(f"  API User: {self.api_user}")
        print(f"  Client IP: {self.client_ip}")
        print(f"  API Key: {'Present' if self.api_key else 'Missing'}")

        if not all([self.api_user, self.api_key]):
            missing = []
            if not self.api_user: missing.append('NAMECHEAP_API_USER')
            if not self.api_key: missing.append('NAMECHEAP_API_KEY')
            raise NamecheapAPIError(f"Missing required environment variables: {', '.join(missing)}")

        if not self.client_ip:
            raise NamecheapAPIError("Could not detect outbound IP address")

    def _detect_outbound_ip(self) -> str:
        """Auto-detect our actual outbound IP address"""
        try:
            import requests
            response = requests.get('https://httpbin.org/ip', timeout=10)
            ip = response.json().get('origin', '').strip()
            print(f"🔍 Auto-detected outbound IP: {ip}")
            return ip
        except Exception as e:
            print(f"❌ Failed to auto-detect IP: {e}")
            # Fallback to environment variable if detection fails
            fallback_ip = os.environ.get('NAMECHEAP_CLIENT_IP', '44.226.145.213')
            print(f"🔧 Using fallback IP from environment: {fallback_ip}")
            return fallback_ip

        # Check for placeholder values
        placeholder_indicators = ['YOUR_NAMECHEAP', 'YOUR_API', 'PLACEHOLDER', 'CHANGE_ME']
        if self.api_user and any(indicator in str(self.api_user).upper() for indicator in placeholder_indicators):
            raise NamecheapAPIError(f"NAMECHEAP_API_USER contains placeholder value: '{self.api_user}'. Please set actual Namecheap API credentials in Render environment variables.")
        if self.api_key and any(indicator in str(self.api_key).upper() for indicator in placeholder_indicators):
            raise NamecheapAPIError(f"NAMECHEAP_API_KEY contains placeholder value. Please set actual Namecheap API credentials in Render environment variables.")
    

    def _make_request(self, command: str, **params) -> Dict:
        """Make API request to Namecheap with rate limiting"""

        wait_time = self.rate_limit.should_wait()
        if wait_time > 0:
            print(f"Rate limit protection: waiting {wait_time:.1f}s before request")
            time.sleep(wait_time)

        self.rate_limit.record_request()

        # Base parameters for all requests
        base_params = {
            'ApiUser': self.api_user,
            'ApiKey': self.api_key,
            'UserName': self.username,
            'Command': command,
            'ClientIp': self.client_ip
        }
        
        # Merge with specific command parameters
        all_params = {**base_params, **params}
        
        print(f"Making Namecheap API request: {command}")
        print(f"Parameters: {list(all_params.keys())}")
        
        try:
            response = requests.get(self.base_url, params=all_params, timeout=30)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
            print(f"Response content (first 500 chars): {response.text[:500]}")
            
            # Try to parse XML response
            try:
                root = ET.fromstring(response.content)
                print(f"XML root tag: {root.tag}")
                print(f"XML root attributes: {root.attrib}")
                
                # Handle XML namespace - Namecheap uses xmlns="http://api.namecheap.com/xml.response"
                namespace = {'nc': 'http://api.namecheap.com/xml.response'}
                
                # Check for API errors
                errors = root.find('.//nc:Errors', namespace) or root.find('.//Errors')
                if errors is not None and len(errors) > 0:
                    error_msg = errors[0].text if errors[0].text else "Unknown API error"
                    print(f"Namecheap API Error: {error_msg}")
                    raise NamecheapAPIError(f"Namecheap API Error: {error_msg}")
                
                # Check API status
                status = root.get('Status', 'Unknown')
                print(f"API Response Status: {status}")
                
                if status != 'OK':
                    print(f"❌ API returned non-OK status: {status}")
                    return None
                
                # Convert to dict and log structure
                result = self._xml_to_dict(root)
                print(f"Parsed result type: {type(result)}")
                if isinstance(result, dict):
                    print(f"Parsed result keys: {list(result.keys())}")
                    # Log domain count if available
                    if 'CommandResponse' in result:
                        cmd_resp = result['CommandResponse']
                        if isinstance(cmd_resp, dict) and 'DomainGetListResult' in cmd_resp:
                            domain_result = cmd_resp['DomainGetListResult']
                            if isinstance(domain_result, dict) and 'Domain' in domain_result:
                                domains = domain_result['Domain']
                                domain_count = len(domains) if isinstance(domains, list) else (1 if domains else 0)
                                print(f"🌐 Found {domain_count} domains in API response")
                else:
                    print(f"Parsed result: {result}")
                
                return result
                
            except ET.ParseError as xml_error:
                print(f"❌ XML parsing failed: {xml_error}")
                print(f"Full response content: {response.text}")
                raise NamecheapAPIError(f"Invalid XML response: {xml_error}")
            
        except requests.RequestException as e:
            error_msg = str(e).lower()
            if "too many requests" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                print(f"Rate limit hit: {e}")
                self.rate_limit.set_paused(900, f"Rate limit exceeded: {e}")
                raise NamecheapAPIError(f"Rate limit exceeded - pausing for 15 minutes: {str(e)}")
            print(f"Request failed: {e}")
            raise NamecheapAPIError(f"API request failed: {str(e)}")
        except Exception as e:
            error_msg = str(e).lower()
            if "too many requests" in error_msg or "rate limit" in error_msg:
                print(f"Rate limit hit: {e}")
                self.rate_limit.set_paused(900, f"Rate limit exceeded: {e}")
                raise NamecheapAPIError(f"Rate limit exceeded - pausing for 15 minutes: {str(e)}")
            print(f"Unexpected error: {e}")
            raise NamecheapAPIError(f"Unexpected error: {str(e)}")
    
    def _xml_to_dict(self, element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes as part of the main dict
        if element.attrib:
            result.update(element.attrib)
        
        # Add text content if exists
        if element.text and element.text.strip():
            if element.attrib or len(element) > 0:
                result['_text'] = element.text.strip()
            else:
                # If no attributes and no children, just return the text
                return element.text.strip()
        
        # Process child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # Convert to list if multiple elements with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        # If result only has attributes, make sure we return them
        return result if result else None
    
    def test_connection(self) -> bool:
        """Test API connection and credentials"""
        try:
            print(f"Testing connection with IP: {self.client_ip}")
            
            # Use getList command to test connection
            response = self._make_request('namecheap.domains.getList')
            
            print(f"API Response keys: {list(response.keys()) if response else 'None'}")
            
            # Check if response is successful - handle namespaced response
            if response and isinstance(response, dict):
                # Check for Status attribute (should be 'OK')
                status = response.get('Status', 'Unknown')
                print(f"API Response Status: {status}")
                
                if status == 'OK':
                    # Look for CommandResponse with namespace handling
                    cmd_response = None
                    for key, value in response.items():
                        if 'CommandResponse' in key:
                            cmd_response = value
                            break
                    
                    if cmd_response and isinstance(cmd_response, dict):
                        print("✅ Namecheap API connection successful")
                        return True
                    else:
                        print("❌ No CommandResponse found in API response")
                        return False
                else:
                    print(f"❌ API returned status: {status}")
                    return False
            else:
                print("❌ Unexpected API response format")
                print(f"Response sample: {str(response)[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Namecheap API connection failed: {e}")
            return False
    
    def get_domain_list(self, page: int = 1, page_size: int = 100) -> List[Dict]:
        """Get list of all domains in account with pagination"""
        try:
            # Use pagination parameters to get more domains
            response = self._make_request(
                'namecheap.domains.getList',
                PageSize=page_size,
                Page=page
            )
            
            # Navigate to domain data - handle namespaced keys
            domains = []
            
            # Find CommandResponse (may be namespaced)
            command_response = None
            for key, value in response.items():
                if 'CommandResponse' in key:
                    command_response = value
                    break
            
            if not command_response:
                print("❌ No CommandResponse found")
                return []
            
            # Find DomainGetListResult
            domain_result = None
            for key, value in command_response.items():
                if 'DomainGetListResult' in key:
                    domain_result = value
                    break
            
            if not domain_result:
                print("❌ No DomainGetListResult found")
                return []
            
            # Get pagination info
            paging_info = domain_result.get('Paging', {})
            if isinstance(paging_info, dict):
                total_items = paging_info.get('TotalItems', 0)
                current_page = paging_info.get('CurrentPage', page)
                page_size_actual = paging_info.get('PageSize', page_size)
                print(f"📄 Page {current_page}: {total_items} total domains, {page_size_actual} per page")
            
            # Find Domain data (may be namespaced or direct)
            domain_data = None
            for key, value in domain_result.items():
                if 'Domain' in key or key == 'Domain':
                    domain_data = value
                    break
            
            if not domain_data:
                print("❌ No Domain data found")
                return []
            
            # Handle single domain or list of domains
            if isinstance(domain_data, dict):
                domain_data = [domain_data]
            
            print(f"🌐 Processing {len(domain_data)} domains from API page {page}")
            
            for domain in domain_data:
                if isinstance(domain, dict):
                    domains.append({
                        'name': domain.get('Name', ''),
                        'user': domain.get('User', ''),
                        'created': domain.get('Created', ''),
                        'expires': domain.get('Expires', ''),
                        'auto_renew': domain.get('AutoRenew', False)
                    })
            
            print(f"Retrieved {len(domains)} domains from page {page}")
            return domains
            
        except Exception as e:
            print(f"Error getting domain list page {page}: {e}")
            return []
    
    def get_all_domains_paginated(self) -> List[Dict]:
        """Get ALL domains by fetching all pages"""
        import time

        all_domains = []
        page = 1
        page_size = 100  # Request 100 per page, but Namecheap might limit to 20
        total_expected = None

        while True:
            print(f"🔄 Fetching domains page {page} (requesting {page_size} per page)...")

            # Add small delay between requests to avoid rate limiting (except first page)
            if page > 1:
                time.sleep(3.0)  # 3s delay between pages (Namecheap: 20 req/min)

            page_domains = self.get_domain_list(page, page_size)

            if not page_domains:
                print(f"✅ No more domains on page {page}. Total: {len(all_domains)}")
                break

            print(f"📄 Got {len(page_domains)} domains on page {page}")
            all_domains.extend(page_domains)

            # Check if we've fetched all domains based on total count
            if total_expected is None:
                # Get total from first page response (set by get_domain_list)
                # This is a rough estimate since get_domain_list logs it but doesn't return it
                # We'll rely on empty response as termination condition
                pass

            # If we got fewer domains than requested, we're likely on the last page
            if len(page_domains) < page_size:
                print(f"✅ Last page detected (got {len(page_domains)} < {page_size}). Total: {len(all_domains)}")
                break

            # Continue to next page
            page += 1

            # Safety check to avoid infinite loops (increased for large accounts)
            if page > 200:  # Increased from 100 to handle up to 4000 domains
                print(f"⚠️ Reached maximum page limit ({page-1} pages). Total domains: {len(all_domains)}")
                break

        print(f"✅ Domain fetching complete. Total domains retrieved: {len(all_domains)}")
        return all_domains
    
    def get_email_forwarding(self, domain: str) -> List[Dict]:
        """Get current email forwarding settings for a domain"""
        try:
            response = self._make_request(
                'namecheap.domains.dns.getEmailForwarding',
                DomainName=domain
            )
            
            # Navigate to email forwarding data
            forwards = []
            api_response = response.get('ApiResponse', {})
            command_response = api_response.get('CommandResponse', {})
            email_result = command_response.get('DomainDNSGetEmailForwardingResult', {})
            
            forward_data = email_result.get('Forward', [])
            
            # Handle single forward or list of forwards
            if isinstance(forward_data, dict):
                forward_data = [forward_data]
            
            for forward in forward_data:
                if isinstance(forward, dict):
                    forwards.append({
                        'from': forward.get('From', ''),
                        'to': forward.get('To', '')
                    })
            
            print(f"Retrieved {len(forwards)} forwarding rules for {domain}")
            return forwards
            
        except Exception as e:
            print(f"Error getting email forwarding for {domain}: {e}")
            return []
    
    def get_domain_redirections(self, domain: str) -> List[Dict]:
        """Get domain URL redirections for a domain"""
        try:
            # Split domain into SLD and TLD as required by Namecheap API
            # For domains like example.com -> SLD=example, TLD=com
            # For domains like example.co.uk -> SLD=example, TLD=co.uk
            domain_parts = domain.split('.')
            if len(domain_parts) < 2:
                print(f"❌ Invalid domain format: {domain}")
                return []
            
            # Handle common multi-part TLDs
            common_tlds = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au', 'co.nz', 'net.nz', 'org.nz']
            
            sld = domain_parts[0]  # First part is always SLD
            tld = '.'.join(domain_parts[1:])  # Rest is TLD
            
            # For multi-part TLDs, adjust accordingly
            for common_tld in common_tlds:
                if domain.endswith('.' + common_tld):
                    sld = domain.replace('.' + common_tld, '')
                    tld = common_tld
                    break
            
            print(f"🔍 Getting DNS records for {domain} (SLD: {sld}, TLD: {tld})")
            
            response = self._make_request(
                'namecheap.domains.dns.getHosts',
                SLD=sld,
                TLD=tld
            )
            
            # Navigate to domain redirections data - handle namespaced keys
            redirections = []
            
            # Find CommandResponse (may be namespaced)
            command_response = None
            for key, value in response.items():
                if 'CommandResponse' in key:
                    command_response = value
                    break
            
            if not command_response:
                print(f"❌ No CommandResponse found for {domain}")
                return []
            
            # Find DomainDNSGetHostsResult
            hosts_result = None
            for key, value in command_response.items():
                if 'DomainDNSGetHostsResult' in key:
                    hosts_result = value
                    break
            
            if not hosts_result:
                print(f"❌ No DomainDNSGetHostsResult found for {domain}")
                return []
            
            # Find Host data (may be namespaced or direct)
            host_data = None
            for key, value in hosts_result.items():
                if 'Host' in key or key == 'Host' or 'host' in key:
                    host_data = value
                    break
            
            # Also try looking for lowercase 'host' key directly
            if not host_data and 'host' in hosts_result:
                host_data = hosts_result['host']
            
            print(f"🔍 Available keys in hosts_result: {list(hosts_result.keys())}")
            
            if not host_data:
                print(f"No Host data found for {domain}")
                return []
            
            # Handle single host or list of hosts
            if isinstance(host_data, dict):
                host_data = [host_data]
            
            print(f"🔗 Processing {len(host_data)} host records for {domain}")
            
            # Look for URL redirections (Type='URL' or 'URL301' or 'URL302')
            for host in host_data:
                if isinstance(host, dict):
                    host_type = host.get('Type', '').upper()
                    host_name = host.get('Name', '@')
                    host_address = host.get('Address', '')
                    
                    print(f"  📋 Host record: {host_name} -> {host_type} -> {host_address}")
                    
                    # Check for URL redirect types
                    if host_type in ['URL', 'URL301', 'URL302', 'REDIRECT']:
                        redirect_type = 'URL Redirect (301)' if host_type == 'URL301' else 'URL Redirect'
                        redirections.append({
                            'type': redirect_type,
                            'target': host_address,
                            'name': host_name
                        })
                        print(f"  ✅ Found redirect: {host_name} -> {host_address}")
            
            print(f"Retrieved {len(redirections)} URL redirections for {domain}")
            return redirections
            
        except Exception as e:
            print(f"Error getting domain redirections for {domain}: {e}")
            return []
    
    def set_email_forwarding(self, domain: str, forwarding_rules: List[Dict]) -> bool:
        """
        Set email forwarding for a domain
        
        Args:
            domain: Domain name
            forwarding_rules: List of {'from': 'alias', 'to': 'destination@email.com'}
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build forwarding parameters
            params = {'DomainName': domain}
            
            # Add each forwarding rule
            for i, rule in enumerate(forwarding_rules, 1):
                params[f'MailBox{i}'] = rule['from']
                params[f'ForwardTo{i}'] = rule['to']
            
            print(f"Setting {len(forwarding_rules)} forwarding rules for {domain}")
            
            response = self._make_request(
                'namecheap.domains.dns.setEmailForwarding',
                **params
            )
            
            # Check if successful
            api_response = response.get('ApiResponse', {})
            command_response = api_response.get('CommandResponse', {})
            result = command_response.get('DomainDNSSetEmailForwardingResult', {})
            
            is_success = result.get('IsSuccess') == 'true'
            
            if is_success:
                print(f"✅ Successfully set email forwarding for {domain}")
            else:
                print(f"❌ Failed to set email forwarding for {domain}")
            
            return is_success
            
        except Exception as e:
            print(f"❌ Error setting email forwarding for {domain}: {e}")
            return False
    
    def set_domain_redirection_safe(self, domain: str, name: str, target: str) -> bool:
        """
        SAFER version: Set domain URL redirection with better verification
        This is a research function to understand the data structure better
        """
        try:
            print(f"🔍 [SAFE MODE] Analyzing DNS structure for {domain}...")

            # Get existing hosts to understand the structure
            existing_hosts = self._get_all_hosts(domain)

            print(f"📋 Found {len(existing_hosts)} existing DNS records:")
            print(f"📋 Raw data structure: {existing_hosts}")

            # Analyze what we have
            analysis = {
                "total_records": len(existing_hosts),
                "url_redirects": [],
                "other_records": [],
                "record_types": set()
            }

            for host in existing_hosts:
                record_type = host.get('Type', 'UNKNOWN')
                analysis["record_types"].add(record_type)

                if record_type == 'URL':
                    analysis["url_redirects"].append({
                        "name": host.get('Name'),
                        "target": host.get('Address'),
                        "ttl": host.get('TTL')
                    })
                else:
                    analysis["other_records"].append({
                        "name": host.get('Name'),
                        "type": record_type,
                        "address": host.get('Address'),
                        "ttl": host.get('TTL'),
                        "mx_pref": host.get('MXPref', '')
                    })

            print(f"📊 ANALYSIS:")
            print(f"   Total records: {analysis['total_records']}")
            print(f"   URL redirects: {len(analysis['url_redirects'])}")
            print(f"   Other DNS records: {len(analysis['other_records'])}")
            print(f"   Record types found: {analysis['record_types']}")

            # Check if it's safe to proceed
            is_safe = len(analysis['other_records']) == 0
            print(f"🛡️  Safe to modify: {is_safe}")

            if not is_safe:
                print(f"⚠️  DANGER: Domain has {len(analysis['other_records'])} non-URL DNS records")
                print(f"⚠️  Modifying would delete: {[r['type'] for r in analysis['other_records']]}")
                return False

            print(f"✅ Domain only has URL redirects - safe to proceed")
            return True

        except Exception as e:
            print(f"❌ Error in safe redirect analysis: {e}")
            return False

    def set_domain_redirection(self, domain: str, name: str, target: str) -> bool:
        """SAFE redirect update with complete DNS backup and restore"""
        try:
            print(f"🔄 SAFE redirect update for {domain}: {name} -> {target}")

            # Import database here to avoid circular imports
            from models import Database
            db = Database()

            # STEP 1: Get current DNS records and backup
            print(f"📋 Step 1: Backing up current DNS records...")
            existing_hosts = self._get_all_hosts(domain)

            if not existing_hosts:
                print(f"❌ Could not fetch DNS records for {domain}")
                return False

            print(f"📋 Found {len(existing_hosts)} DNS records to backup")

            # Backup all current DNS records
            backup_success = db.backup_dns_records(domain, existing_hosts)
            if not backup_success:
                print(f"❌ Failed to backup DNS records - aborting update")
                return False

            # STEP 2: Update redirect in backup and get complete record set
            print(f"🔄 Step 2: Updating redirect in backup...")
            complete_records = db.update_redirect_in_backup(domain, name, target)

            if not complete_records:
                print(f"❌ Failed to update redirect in backup")
                return False

            # STEP 2.5: Filter out any remaining parking page records that might conflict
            print(f"🔄 Step 2.5: Filtering out parking page records...")
            original_count = len(complete_records)
            complete_records = [r for r in complete_records if not self._is_parking_page_record(r, name)]
            filtered_count = original_count - len(complete_records)
            if filtered_count > 0:
                print(f"🗑️  Filtered out {filtered_count} parking page record(s)")

            print(f"📦 Will send {len(complete_records)} DNS records to Namecheap")

            # Log what we're sending with detailed breakdown
            url_redirects = [r for r in complete_records if r['Type'] == 'URL']
            mx_records = [r for r in complete_records if r['Type'] == 'MX']
            a_records = [r for r in complete_records if r['Type'] == 'A']
            cname_records = [r for r in complete_records if r['Type'] == 'CNAME']
            txt_records = [r for r in complete_records if r['Type'] == 'TXT']
            other_records = [r for r in complete_records if r['Type'] not in ['URL', 'MX', 'A', 'CNAME', 'TXT']]

            print(f"📊 Sending to Namecheap:")
            if mx_records:
                print(f"  📧 {len(mx_records)} MX records (email)")
            if a_records:
                print(f"  🌐 {len(a_records)} A records")
            if cname_records:
                print(f"  🔗 {len(cname_records)} CNAME records")
            if txt_records:
                print(f"  📄 {len(txt_records)} TXT records (SPF/DKIM/DMARC)")
            if url_redirects:
                print(f"  ↗️  {len(url_redirects)} URL redirects")
            if other_records:
                print(f"  📝 {len(other_records)} other records")

            # STEP 3: Send complete record set to Namecheap
            print(f"🚀 Step 3: Sending complete DNS records to Namecheap...")

            # Split domain for Namecheap API
            domain_parts = domain.split('.')
            if len(domain_parts) < 2:
                print(f"❌ Invalid domain format: {domain}")
                return False

            sld = domain_parts[0]
            tld = '.'.join(domain_parts[1:])

            # Handle common multi-part TLDs
            common_tlds = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au']
            for common_tld in common_tlds:
                if domain.endswith('.' + common_tld):
                    sld = domain.replace('.' + common_tld, '')
                    tld = common_tld
                    break

            # Build setHosts parameters with ALL records
            params = {'SLD': sld, 'TLD': tld}

            for i, record in enumerate(complete_records, 1):
                params[f'HostName{i}'] = record['Name']
                params[f'RecordType{i}'] = record['Type']
                params[f'Address{i}'] = record['Address']
                params[f'TTL{i}'] = record['TTL']
                if record.get('MXPref'):
                    params[f'MXPref{i}'] = record['MXPref']

            # Make API call with complete record set
            response = self._make_request('namecheap.domains.dns.setHosts', **params)

            # STEP 4: Verify response
            command_response = None
            for key, value in response.items():
                if 'CommandResponse' in key:
                    command_response = value
                    break

            if command_response:
                hosts_result = None
                for key, value in command_response.items():
                    if 'DomainDNSSetHostsResult' in key:
                        hosts_result = value
                        break

                if hosts_result and hosts_result.get('IsSuccess') == 'true':
                    print(f"✅ Successfully updated redirect for {domain}")
                    print(f"✅ All {len(complete_records)} DNS records sent successfully")

                    # STEP 5: Verify DNS records are actually set correctly
                    print(f"🔍 Step 5: Verifying DNS records after update...")
                    import time
                    time.sleep(3)  # Wait for DNS propagation

                    # Get updated DNS records to verify
                    updated_hosts = self._get_all_hosts(domain)
                    if updated_hosts and len(updated_hosts) >= len(complete_records):
                        print(f"✅ Verification passed: {len(updated_hosts)} records found")
                        return True
                    else:
                        print(f"⚠️ Verification warning: Expected {len(complete_records)}, found {len(updated_hosts) if updated_hosts else 0}")
                        return True  # Still consider success if API returned success
                else:
                    print(f"❌ Namecheap API returned failure: {hosts_result}")
                    return False

            print(f"❌ Unexpected response format from Namecheap")
            return False

        except Exception as e:
            print(f"❌ Error in safe redirect update: {e}")
            return False

    def verify_domain_redirection(self, domain: str, name: str, expected_target: str) -> bool:
        """Verify that domain redirection was actually set correctly"""
        try:
            redirections = self.get_domain_redirections(domain)

            for redirect in redirections:
                if redirect.get('name') == name and redirect.get('target') == expected_target:
                    print(f"✅ Verified redirection for {domain}: {name} -> {expected_target}")
                    return True

            print(f"❌ Verification failed for {domain}: {name} -> {expected_target}")
            return False

        except Exception as e:
            print(f"❌ Error verifying domain redirection: {str(e)}")
            return False
    
    def _is_parking_page_record(self, record: Dict, redirect_name: str) -> bool:
        """Check if a DNS record is a parking page that should be removed when setting a redirect"""
        record_name = record.get('Name', '@')
        record_type = record.get('Type', '').upper()
        record_address = record.get('Address', '').lower()

        # Only check records for the same name as the redirect we're setting
        if record_name != redirect_name:
            return False

        # Check for known parking page indicators
        parking_indicators = [
            'parkingpage.namecheap.com',
            'parking',
            'namecheap.com'
        ]

        # Remove CNAME or A records pointing to parking services
        if record_type in ['CNAME', 'A']:
            for indicator in parking_indicators:
                if indicator in record_address:
                    print(f"🎯 Detected parking page: {record_name} {record_type} -> {record_address}")
                    return True

        return False

    def _get_all_hosts(self, domain: str) -> List[Dict]:
        """Get all DNS host records for a domain"""
        try:
            # Split domain into SLD and TLD as required by Namecheap API
            domain_parts = domain.split('.')
            if len(domain_parts) < 2:
                print(f"❌ Invalid domain format: {domain}")
                return []
            
            # Handle common multi-part TLDs
            common_tlds = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au', 'co.nz', 'net.nz', 'org.nz']
            
            sld = domain_parts[0]  # First part is always SLD
            tld = '.'.join(domain_parts[1:])  # Rest is TLD
            
            # For multi-part TLDs, adjust accordingly
            for common_tld in common_tlds:
                if domain.endswith('.' + common_tld):
                    sld = domain.replace('.' + common_tld, '')
                    tld = common_tld
                    break
            
            response = self._make_request(
                'namecheap.domains.dns.getHosts',
                SLD=sld,
                TLD=tld
            )

            hosts = []

            # Find CommandResponse (may be namespaced)
            command_response = None
            for key, value in response.items():
                if 'CommandResponse' in key:
                    command_response = value
                    break

            if not command_response:
                return []

            # Find DomainDNSGetHostsResult
            hosts_result = None
            for key, value in command_response.items():
                if 'DomainDNSGetHostsResult' in key:
                    hosts_result = value
                    break

            if not hosts_result:
                return []

            # Find Host data (may be namespaced or direct)
            # Note: Namecheap uses lowercase 'host' in the response
            host_data = None
            for key, value in hosts_result.items():
                if 'host' in key.lower():
                    host_data = value
                    break

            if not host_data:
                return []
            
            # Handle single host or list of hosts
            if isinstance(host_data, dict):
                host_data = [host_data]

            if not host_data:
                return []

            # Normalize the host data format and categorize by type
            normalized_hosts = []
            record_types = {}

            for host in host_data:
                if isinstance(host, dict):
                    # Map lowercase field names to expected format
                    normalized_host = {
                        'Name': host.get('Name', host.get('name', '@')),
                        'Type': host.get('Type', host.get('type', '')),
                        'Address': host.get('Address', host.get('address', '')),
                        'TTL': host.get('TTL', host.get('ttl', '1800')),
                        'MXPref': host.get('MXPref', host.get('mxpref', ''))
                    }
                    normalized_hosts.append(normalized_host)

                    record_type = normalized_host['Type']
                    record_types[record_type] = record_types.get(record_type, 0) + 1

            return normalized_hosts
            
        except Exception as e:
            print(f"Error getting all hosts for {domain}: {e}")
            return []

class EmailRedirectionManager:
    """Manager for bulk email redirection operations"""
    
    def __init__(self):
        """Initialize the email redirection manager"""
        self.api_client = NamecheapAPIClient()
        self.results = []
        
        # Test connection on initialization
        if not self.api_client.test_connection():
            print("⚠️ Warning: Namecheap API connection test failed")
    
    def get_all_domains(self) -> List[str]:
        """Get all domains from Namecheap account"""
        domain_data = self.api_client.get_all_domains_paginated()
        return [domain['name'] for domain in domain_data]
    
    def bulk_set_forwarding(self, domains: List[str], forwarding_rules: List[Dict]) -> Dict:
        """
        Set email forwarding for multiple domains
        
        Args:
            domains: List of domain names
            forwarding_rules: List of forwarding rules to apply to each domain
        
        Returns:
            Results summary
        """
        start_time = datetime.now()
        
        results = {
            'successful': [],
            'failed': [],
            'total_processed': 0,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration': None
        }
        
        print(f"🚀 Starting bulk forwarding for {len(domains)} domains...")
        print(f"📧 Forwarding rules:")
        for rule in forwarding_rules:
            print(f"   {rule['from']} → {rule['to']}")
        
        for i, domain in enumerate(domains, 1):
            print(f"\n📧 Processing {i}/{len(domains)}: {domain}")
            
            try:
                success = self.api_client.set_email_forwarding(domain, forwarding_rules)
                
                if success:
                    results['successful'].append(domain)
                else:
                    results['failed'].append({
                        'domain': domain, 
                        'error': 'API returned failure status'
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'domain': domain, 
                    'error': str(e)
                })
            
            results['total_processed'] = i
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        results['end_time'] = end_time.isoformat()
        results['duration'] = str(duration)
        
        # Print summary
        print(f"\n🎯 BULK FORWARDING COMPLETE:")
        print(f"   ✅ Successful: {len(results['successful'])}")
        print(f"   ❌ Failed: {len(results['failed'])}")
        print(f"   ⏱️ Duration: {duration}")
        
        return results
    
    def export_results(self, results: Dict, filename: str = None) -> str:
        """Export results to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_redirect_results_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write header
                writer.writerow(['Domain', 'Status', 'Error'])
                
                # Write successful domains
                for domain in results['successful']:
                    writer.writerow([domain, 'Success', ''])
                
                # Write failed domains
                for failed in results['failed']:
                    writer.writerow([failed['domain'], 'Failed', failed['error']])
                
            print(f"📄 Results exported to: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting results: {e}")
            return None

# Example usage for testing
if __name__ == "__main__":
    """Test the email redirection functionality"""
    
    try:
        # Initialize manager
        manager = EmailRedirectionManager()
        
        # Test with a few domains
        test_domains = ['example.com', 'test.com']  # Replace with your domains
        
        # Example forwarding rules
        forwarding_rules = [
            {'from': 'info', 'to': 'admin@yourmainmail.com'},
            {'from': 'contact', 'to': 'admin@yourmainmail.com'}
        ]
        
        # Get domains from account
        print("Getting domains from Namecheap account...")
        all_domains = manager.get_all_domains()
        print(f"Found {len(all_domains)} domains in account")
        
        if all_domains:
            # Use first 2 domains for testing
            test_domains = all_domains[:2]
            
            print(f"\nTesting with domains: {test_domains}")
            
            # Process domains
            results = manager.bulk_set_forwarding(test_domains, forwarding_rules)
            
            # Export results
            filename = manager.export_results(results)
            
            print(f"\nTest completed. Results saved to: {filename}")
        else:
            print("No domains found in account. Please check your API credentials.")
            
    except Exception as e:
        print(f"Test failed: {e}")