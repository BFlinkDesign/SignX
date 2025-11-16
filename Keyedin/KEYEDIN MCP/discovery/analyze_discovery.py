"""
KeyedIn Discovery Analysis Utilities

Tools for exploring, analyzing, and visualizing discovery data.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
import argparse


class DiscoveryAnalyzer:
    """Analyze and query discovery data"""
    
    def __init__(self, discovery_file: str):
        self.discovery_file = Path(discovery_file)
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """Load discovery JSON"""
        with open(self.discovery_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def print_summary(self):
        """Print discovery summary statistics"""
        print("=" * 70)
        print("KEYEDIN DISCOVERY SUMMARY")
        print("=" * 70)
        print()
        
        stats = self.data.get('statistics', {})
        
        print(f"Discovery Date: {self.data.get('timestamp', 'Unknown')}")
        print(f"Base URL: {self.data.get('base_url', 'Unknown')}")
        print()
        
        print("COVERAGE STATISTICS:")
        print(f"  Total Endpoints: {stats.get('total_endpoints', 0)}")
        print(f"  Total Forms: {stats.get('total_forms', 0)}")
        print(f"  Total Entities: {stats.get('total_entities', 0)}")
        print(f"  URLs Visited: {stats.get('urls_visited', 0)}")
        print()
        
        # Section breakdown
        endpoints = self.data.get('endpoints', [])
        by_section = defaultdict(int)
        for e in endpoints:
            by_section[e.get('section', 'Unknown')] += 1
        
        print("ENDPOINTS BY SECTION:")
        for section in sorted(by_section.keys()):
            print(f"  {section:35} {by_section[section]:3} endpoints")
        print()
        
        # Form breakdown
        forms = self.data.get('forms', [])
        by_section_forms = defaultdict(int)
        for f in forms:
            by_section_forms[f.get('section', 'Unknown')] += 1
        
        print("FORMS BY SECTION:")
        for section in sorted(by_section_forms.keys()):
            print(f"  {section:35} {by_section_forms[section]:3} forms")
        print()
        
        # Entities
        entities = self.data.get('entities', {})
        print("DISCOVERED ENTITIES:")
        for name in sorted(entities.keys()):
            field_count = len(entities[name].get('fields', []))
            print(f"  {name:35} {field_count:3} fields")
        print()
    
    def find_endpoints(self, section: str = None, search: str = None):
        """Find endpoints by section or search term"""
        endpoints = self.data.get('endpoints', [])
        
        results = endpoints
        
        if section:
            results = [e for e in results if section.lower() in e.get('section', '').lower()]
        
        if search:
            results = [e for e in results 
                      if search.lower() in e.get('url', '').lower() 
                      or search.lower() in e.get('purpose', '').lower()]
        
        print(f"\nFound {len(results)} endpoints:")
        print()
        
        for e in results:
            print(f"Section: {e.get('section', 'Unknown')}")
            print(f"  URL: {e.get('url', 'N/A')}")
            print(f"  Method: {e.get('method', 'GET')}")
            print(f"  Purpose: {e.get('purpose', 'N/A')}")
            if e.get('parameters'):
                print(f"  Parameters: {', '.join(e['parameters'].keys())}")
            print()
    
    def find_forms(self, section: str = None):
        """Find forms by section"""
        forms = self.data.get('forms', [])
        
        if section:
            forms = [f for f in forms if section.lower() in f.get('section', '').lower()]
        
        print(f"\nFound {len(forms)} forms:")
        print()
        
        for f in forms:
            print(f"Form ID: {f.get('form_id', 'Unknown')}")
            print(f"  Section: {f.get('section', 'Unknown')}")
            print(f"  Action: {f.get('action_url', 'N/A')}")
            print(f"  Fields: {len(f.get('fields', []))}")
            print(f"  Purpose: {f.get('purpose', 'N/A')}")
            print()
    
    def analyze_entity(self, entity_name: str):
        """Show detailed entity information"""
        entities = self.data.get('entities', {})
        
        entity = entities.get(entity_name)
        if not entity:
            print(f"Entity '{entity_name}' not found.")
            print(f"Available entities: {', '.join(sorted(entities.keys()))}")
            return
        
        print(f"\nENTITY: {entity_name}")
        print("=" * 70)
        print()
        
        print(f"Discovered In: {', '.join(entity.get('discovered_in', []))}")
        print()
        
        fields = entity.get('fields', [])
        print(f"FIELDS ({len(fields)}):")
        for field in fields:
            print(f"  - {field.get('name', 'Unknown'):30} ({field.get('type', 'unknown')})")
        print()
        
        relationships = entity.get('relationships', [])
        if relationships:
            print("RELATIONSHIPS:")
            for rel in relationships:
                print(f"  - {rel}")
            print()
    
    def generate_endpoint_code(self, output_file: str = None):
        """Generate Python constants file for endpoints"""
        endpoints = self.data.get('endpoints', [])
        
        # Group by section
        by_section = defaultdict(list)
        for e in endpoints:
            section = e.get('section', 'Unknown')
            by_section[section].append(e)
        
        lines = []
        lines.append('"""')
        lines.append('KeyedIn Endpoint Registry')
        lines.append('')
        lines.append(f'Generated from discovery data: {self.data.get("timestamp", "Unknown")}')
        lines.append('"""')
        lines.append('')
        lines.append('KEYEDIN_ENDPOINTS = {')
        
        for section in sorted(by_section.keys()):
            section_key = section.lower().replace(' ', '_').replace('-', '_')
            lines.append(f'    "{section_key}": {{')
            
            for endpoint in by_section[section]:
                url = endpoint.get('url', '')
                # Extract action name from URL
                action = url.split('/')[-1].split('?')[0].lower().replace('.', '_')
                lines.append(f'        "{action}": "{url}",')
            
            lines.append('    },')
        
        lines.append('}')
        
        code = '\n'.join(lines)
        
        if output_file:
            Path(output_file).write_text(code, encoding='utf-8')
            print(f"Generated endpoint code: {output_file}")
        else:
            print(code)
    
    def export_entity_relationships_mermaid(self, output_file: str = None):
        """Generate Mermaid ERD diagram"""
        entities = self.data.get('entities', {})
        
        lines = []
        lines.append('erDiagram')
        
        # Add entities
        for entity_name, entity in entities.items():
            entity_clean = entity_name.replace(' ', '_').upper()
            lines.append(f'    {entity_clean} {{')
            
            fields = entity.get('fields', [])[:10]  # Limit to 10 for readability
            for field in fields:
                field_name = field.get('name', 'unknown').replace(' ', '_')
                field_type = field.get('type', 'string')
                lines.append(f'        {field_type} {field_name}')
            
            if len(entity.get('fields', [])) > 10:
                lines.append('        string ...')
            
            lines.append('    }')
        
        # Add relationships (simplified - would need more analysis)
        # For now, just show entities
        
        diagram = '\n'.join(lines)
        
        if output_file:
            Path(output_file).write_text(diagram, encoding='utf-8')
            print(f"Generated Mermaid ERD: {output_file}")
        else:
            print(diagram)
    
    def analyze_api_feasibility(self):
        """Quick API feasibility assessment"""
        endpoints = self.data.get('endpoints', [])
        forms = self.data.get('forms', [])
        
        print("\nAPI FEASIBILITY QUICK ASSESSMENT")
        print("=" * 70)
        print()
        
        # Count by response type
        html_count = sum(1 for e in endpoints if e.get('response_type') == 'html')
        json_count = sum(1 for e in endpoints if e.get('response_type') == 'json')
        total = len(endpoints)
        
        print(f"Total Endpoints: {total}")
        print(f"  HTML Responses: {html_count} ({html_count/max(total,1)*100:.1f}%)")
        print(f"  JSON Responses: {json_count} ({json_count/max(total,1)*100:.1f}%)")
        print()
        
        # Determine type
        if json_count > total * 0.3:
            classification = "Type A: API-Friendly ✅"
            recommendation = "Build REST API wrapper with direct endpoints"
        elif html_count > total * 0.8:
            classification = "Type B: Parsable but Messy ⚠️"
            recommendation = "Build REST API wrapper with BeautifulSoup parsing"
        else:
            classification = "Type C: Browser-Dependent ❌"
            recommendation = "Continue with Playwright MCP approach"
        
        print(f"Classification: {classification}")
        print(f"Recommendation: {recommendation}")
        print()
        
        # Implementation estimate
        if total > 50:
            effort = "4-6 weeks"
        elif total > 20:
            effort = "2-4 weeks"
        else:
            effort = "1-2 weeks"
        
        print(f"Estimated Implementation Effort: {effort}")
        print(f"Forms Discovered: {len(forms)} (data entry capabilities)")
        print()


def main():
    parser = argparse.ArgumentParser(description='Analyze KeyedIn discovery data')
    parser.add_argument('discovery_file', help='Path to raw_discovery.json')
    
    subparsers = parser.add_subparsers(dest='command', help='Analysis command')
    
    # Summary command
    subparsers.add_parser('summary', help='Show discovery summary')
    
    # Find endpoints command
    find_ep = subparsers.add_parser('find-endpoints', help='Find endpoints')
    find_ep.add_argument('--section', help='Filter by section')
    find_ep.add_argument('--search', help='Search in URL or purpose')
    
    # Find forms command
    find_form = subparsers.add_parser('find-forms', help='Find forms')
    find_form.add_argument('--section', help='Filter by section')
    
    # Analyze entity command
    analyze = subparsers.add_parser('analyze-entity', help='Analyze specific entity')
    analyze.add_argument('entity', help='Entity name')
    
    # Generate code command
    gen_code = subparsers.add_parser('generate-code', help='Generate endpoint code')
    gen_code.add_argument('--output', help='Output file path')
    
    # Generate ERD command
    gen_erd = subparsers.add_parser('generate-erd', help='Generate Mermaid ERD')
    gen_erd.add_argument('--output', help='Output file path')
    
    # API feasibility command
    subparsers.add_parser('api-feasibility', help='API feasibility assessment')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = DiscoveryAnalyzer(args.discovery_file)
    
    # Execute command
    if args.command == 'summary':
        analyzer.print_summary()
    
    elif args.command == 'find-endpoints':
        analyzer.find_endpoints(section=args.section, search=args.search)
    
    elif args.command == 'find-forms':
        analyzer.find_forms(section=args.section)
    
    elif args.command == 'analyze-entity':
        analyzer.analyze_entity(args.entity)
    
    elif args.command == 'generate-code':
        analyzer.generate_endpoint_code(output_file=args.output)
    
    elif args.command == 'generate-erd':
        analyzer.export_entity_relationships_mermaid(output_file=args.output)
    
    elif args.command == 'api-feasibility':
        analyzer.analyze_api_feasibility()
    
    else:
        # Default to summary if no command
        analyzer.print_summary()


if __name__ == '__main__':
    main()
