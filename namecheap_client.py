"""
Namecheap Email Redirection Client
Handles API communication with Namecheap for bulk email forwarding
"""

import requests
import json
import csv
import os
from typing import Dict, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

class NamecheapAPIError(Exception):
    """Custom exception for Namecheap API errors"""
    pass

class NamecheapAPIClient:
    """Client for Namecheap API operations"""
    
    def __init__(self):
        """Initialize Namecheap API client"""
        self.base_url = "https://api.namecheap.com/xml.response"
        self.api_user = os.environ.get('NAMECHEAP_API_USER')
        self.api_key = os.environ.get('NAMECHEAP_API_KEY')
        self.username = os.environ.get('NAMECHEAP_USERNAME', self.api_user)
        
        # Auto-detect our outbound IP instead of using configured one
        self.client_ip = self._detect_outbound_ip()
        
        print(f"Namecheap API Client initialized:")
        print(f"  API User: {self.api_user}")
        print(f"  Auto-detected Client IP: {self.client_ip}")
        print(f"  API Key: {'Present' if self.api_key else 'Missing'}")
        
        if not all([self.api_user, self.api_key]):
            missing = []
            if not self.api_user: missing.append('NAMECHEAP_API_USER')
            if not self.api_key: missing.append('NAMECHEAP_API_KEY')
            raise NamecheapAPIError(f"Missing required environment variables: {', '.join(missing)}")
        
        if not self.client_ip:
            raise NamecheapAPIError("Could not auto-detect outbound IP address")
    
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
            fallback_ip = os.environ.get('NAMECHEAP_CLIENT_IP')
            if fallback_ip:
                print(f"🔄 Using fallback IP from environment: {fallback_ip}")
                return fallback_ip
            return None
    
    def _make_request(self, command: str, **params) -> Dict:
        """Make API request to Namecheap"""
        
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
            print(f"Request failed: {e}")
            raise NamecheapAPIError(f"API request failed: {str(e)}")
        except Exception as e:
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
            
            # Check if response is successful
            if response and 'ApiResponse' in response:
                api_response = response['ApiResponse']
                if isinstance(api_response, dict) and api_response.get('Status') == 'OK':
                    print("✅ Namecheap API connection successful")
                    return True
                else:
                    print(f"❌ API returned status: {api_response.get('Status') if isinstance(api_response, dict) else 'Unknown'}")
                    return False
            else:
                print("❌ Unexpected API response format")
                print(f"Response sample: {str(response)[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Namecheap API connection failed: {e}")
            return False
    
    def get_domain_list(self) -> List[Dict]:
        """Get list of all domains in account"""
        try:
            response = self._make_request('namecheap.domains.getList')
            
            # Navigate to domain data
            domains = []
            api_response = response.get('ApiResponse', {})
            command_response = api_response.get('CommandResponse', {})
            domain_result = command_response.get('DomainGetListResult', {})
            
            domain_data = domain_result.get('Domain', [])
            
            # Handle single domain or list of domains
            if isinstance(domain_data, dict):
                domain_data = [domain_data]
            
            for domain in domain_data:
                if isinstance(domain, dict):
                    domains.append({
                        'name': domain.get('Name', ''),
                        'user': domain.get('User', ''),
                        'created': domain.get('Created', ''),
                        'expires': domain.get('Expires', ''),
                        'auto_renew': domain.get('AutoRenew', False)
                    })
            
            print(f"Retrieved {len(domains)} domains from account")
            return domains
            
        except Exception as e:
            print(f"Error getting domain list: {e}")
            return []
    
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
        domain_data = self.api_client.get_domain_list()
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