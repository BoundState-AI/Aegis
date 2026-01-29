# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# DEPRECATED: This Python plugin format is deprecated for security reasons.
# Please use the JSON format instead. See amentum_rules.json
# This file will be removed in a future version.

# boundstate/plugins/amentum_rules.py
# Amentum-specific tagging rules for defense and aerospace applications
import re

def get_rules():
    """
    Return tagging rules specific to Amentum's defense, aerospace, and engineering operations.
    
    Compliance: SWE-033 (Requirements Traceability)
    
    Returns:
        List of (tag_name, compiled_regex) tuples
    """
    
    rules = [
        # Defense and military
        ("Defense", re.compile(r'\b(defense|military|DoD|Department of Defense)\b', re.IGNORECASE)),
        ("Defense", re.compile(r'\b(classified|secret|confidential|FOUO)\b', re.IGNORECASE)),
        ("Defense", re.compile(r'\b(security clearance|clearance level|background investigation)\b', re.IGNORECASE)),
        
        # Aerospace
        ("Aerospace", re.compile(r'\b(aerospace|aircraft|aviation|flight|missile)\b', re.IGNORECASE)),
        ("Aerospace", re.compile(r'\b(spacecraft|satellite|launch|orbital|space)\b', re.IGNORECASE)),
        ("Aerospace", re.compile(r'\b(avionics|navigation|guidance|propulsion)\b', re.IGNORECASE)),
        
        # Nuclear and energy
        ("Nuclear", re.compile(r'\b(nuclear|reactor|uranium|plutonium|enrichment)\b', re.IGNORECASE)),
        ("Nuclear", re.compile(r'\b(radiological|radioactive|contamination|decontamination)\b', re.IGNORECASE)),
        ("Nuclear", re.compile(r'\b(waste management|storage|disposal|transport)\b', re.IGNORECASE)),
        
        # Engineering services
        ("Engineering", re.compile(r'\b(engineering|design|analysis|simulation|modeling)\b', re.IGNORECASE)),
        ("Engineering", re.compile(r'\b(systems engineering|software engineering|civil engineering)\b', re.IGNORECASE)),
        ("Engineering", re.compile(r'\b(structural|mechanical|electrical|chemical)\b', re.IGNORECASE)),
        
        # Project management
        ("Project_Management", re.compile(r'\b(project management|schedule|milestone|deliverable)\b', re.IGNORECASE)),
        ("Project_Management", re.compile(r'\b(risk management|cost control|quality assurance)\b', re.IGNORECASE)),
        ("Project_Management", re.compile(r'\b(work breakdown|statement of work|SOW)\b', re.IGNORECASE)),
        
        # Logistics and supply chain
        ("Logistics", re.compile(r'\b(logistics|supply chain|inventory|warehouse)\b', re.IGNORECASE)),
        ("Logistics", re.compile(r'\b(transportation|shipping|delivery|distribution)\b', re.IGNORECASE)),
        ("Logistics", re.compile(r'\b(spare parts|maintenance|repair|overhaul)\b', re.IGNORECASE)),
        
        # Quality and compliance
        ("Quality", re.compile(r'\b(quality|ISO 9001|AS9100|quality management)\b', re.IGNORECASE)),
        ("Quality", re.compile(r'\b(inspection|audit|certification|accreditation)\b', re.IGNORECASE)),
        ("Quality", re.compile(r'\b(nonconformance|corrective action|preventive action)\b', re.IGNORECASE)),
        
        # Safety and health
        ("Safety", re.compile(r'\b(hazard|risk assessment|safety plan|emergency response)\b', re.IGNORECASE)),
        ("Safety", re.compile(r'\b(personal protective equipment|PPE|safety training)\b', re.IGNORECASE)),
        
        # Environmental
        ("Environmental", re.compile(r'\b(environmental|EPA|NEPA|environmental impact)\b', re.IGNORECASE)),
        ("Environmental", re.compile(r'\b(remediation|cleanup|contamination|monitoring)\b', re.IGNORECASE)),
        ("Environmental", re.compile(r'\b(air quality|water quality|soil|groundwater)\b', re.IGNORECASE)),
        
        # Cybersecurity
        ("Cybersecurity", re.compile(r'\b(cybersecurity|information security|cyber|NIST)\b', re.IGNORECASE)),
        ("Cybersecurity", re.compile(r'\b(encryption|authentication|access control|firewall)\b', re.IGNORECASE)),
        ("Cybersecurity", re.compile(r'\b(vulnerability|threat|malware|incident response)\b', re.IGNORECASE)),
        
        # Training and development
        ("Training", re.compile(r'\b(training|education|certification|professional development)\b', re.IGNORECASE)),
        ("Training", re.compile(r'\b(competency|skill|knowledge|learning)\b', re.IGNORECASE)),
        ("Training", re.compile(r'\b(curriculum|course|workshop|seminar)\b', re.IGNORECASE)),
        
        # Facilities and infrastructure
        ("Facilities", re.compile(r'\b(facility|infrastructure|building|construction)\b', re.IGNORECASE)),
        ("Facilities", re.compile(r'\b(maintenance|utilities|HVAC|electrical|plumbing)\b', re.IGNORECASE)),
        ("Facilities", re.compile(r'\b(security|access control|surveillance|perimeter)\b', re.IGNORECASE)),
        
        # Research and development
        ("Research", re.compile(r'\b(research|development|R&D|innovation|technology)\b', re.IGNORECASE)),
        ("Research", re.compile(r'\b(prototype|testing|validation|verification)\b', re.IGNORECASE)),
        ("Research", re.compile(r'\b(experiment|data analysis|report|publication)\b', re.IGNORECASE)),
        
        # Government agencies and customers
        ("Government", re.compile(r'\b(government|federal|state|local|agency)\b', re.IGNORECASE)),
        ("Government", re.compile(r'\b(NASA|DOE|DOD|DHS|EPA|USACE)\b')),
        ("Government", re.compile(r'\b(contract|subcontract|prime|vendor|supplier)\b', re.IGNORECASE)),
        
        # Specific technologies
        ("Technology", re.compile(r'\b(artificial intelligence|AI|machine learning|ML)\b', re.IGNORECASE)),
        ("Technology", re.compile(r'\b(digital|automation|robotics|sensors|IoT)\b', re.IGNORECASE)),
        ("Technology", re.compile(r'\b(cloud|software|database|network|system)\b', re.IGNORECASE)),
        
        # Financial and business
        ("Financial", re.compile(r'\b(financial|budget|cost|revenue|profit)\b', re.IGNORECASE)),
        ("Financial", re.compile(r'\b(accounting|audit|invoice|payment|billing)\b', re.IGNORECASE)),
        ("Financial", re.compile(r'\b(proposal|bid|award|contract value)\b', re.IGNORECASE)),
        
        # Emergency and disaster response
        ("Emergency", re.compile(r'\b(emergency|disaster|response|recovery|continuity)\b', re.IGNORECASE)),
        ("Emergency", re.compile(r'\b(evacuation|shelter|rescue|relief|assistance)\b', re.IGNORECASE)),
        ("Emergency", re.compile(r'\b(hurricane|flood|earthquake|fire|pandemic)\b', re.IGNORECASE)),
    ]
    
    return rules