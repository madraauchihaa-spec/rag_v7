import requests
import json
import time
import os

# API Configuration - Using port 8005 to avoid socket conflicts
API_URL = os.getenv("API_URL", "http://127.0.0.1:8005/query")

# ---------------------------------------------------------
# Test Suite: 15 Real-World Compliance Scenarios
# ---------------------------------------------------------
TEST_SCENARIOS = [
    {
        "id": "TC-001",
        "name": "Fire Exit Blockage",
        "text": "The main fire exit in the finishing department is blocked by cardboard boxes and scrap material.",
        "site_profile": {"industry_type": "Engineering", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-002",
        "name": "Electrical Panel Maintenance",
        "text": "Electrical panels in the utility area are found unlocked and without rubber mats on the floor.",
        "site_profile": {"industry_type": "Textile", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-003",
        "name": "Chemical Spillage Protocol",
        "text": "A liquid chemical drum is leaking in the storage yard, and there is no secondary containment provided.",
        "site_profile": {"industry_type": "Chemical", "mah_status": "MAH"}
    },
    {
        "id": "TC-004",
        "name": "First Aid Boxes Clause",
        "text": "What are the legal requirements for providing first aid boxes based on the number of workers?",
        "site_profile": {"industry_type": "Auto Ancillary", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-005",
        "name": "Working at Height Safety",
        "text": "Workers were seen working on the roof without a safety harness or a stable lifeline system.",
        "site_profile": {"industry_type": "Construction", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-006",
        "name": "Machine Guarding Issue",
        "text": "The rotating parts of the power press machine are exposed and do not have any physical guards.",
        "site_profile": {"industry_type": "Engineering", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-007",
        "name": "Factory License Renewal",
        "text": "Is there a penalty if the factory license renewal application is submitted after the expiration date?",
        "site_profile": {"industry_type": "Agrochemical", "mah_status": "MAH"}
    },
    {
        "id": "TC-008",
        "name": "PPE Non-Compliance",
        "text": "During site round, it was observed that 50% of the workers in the welding area are not wearing safety goggles.",
        "site_profile": {"industry_type": "Fabrication", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-009",
        "name": "Ventilation Legal Query",
        "text": "What as per Factories Act are the standards for ventilation and temperature in the workrooms?",
        "site_profile": {"industry_type": "Pharma", "mah_status": "MAH"}
    },
    {
        "id": "TC-010",
        "name": "Pressure Vessel Testing",
        "text": "The air receiver tank in the compressor room has not been hydrostatically tested in the last 2 years.",
        "site_profile": {"industry_type": "Chemical", "mah_status": "MAH"}
    },
    {
        "id": "TC-011",
        "name": "Hoists and Lifts Stability",
        "text": "The goods lift is used for passenger movement and has no visible stability certificate displayed.",
        "site_profile": {"industry_type": "Logistics", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-012",
        "name": "Welfare Facilities (Legal)",
        "text": "What are the rules for providing a canteen and creche facility to female workers?",
        "site_profile": {"industry_type": "Food Processing", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-013",
        "name": "Fire Detection System",
        "text": "The smoke detectors in the raw material warehouse are disconnected and showing fault on the panel.",
        "site_profile": {"industry_type": "Warehousing", "mah_status": "Non_MAH"}
    },
    {
        "id": "TC-014",
        "name": "Material Handling Risk",
        "text": "Manual handling of 50kg bags is causing ergonomic risks; no mechanical lifting aid is provided.",
        "site_profile": {"industry_type": "Fertilizer", "mah_status": "MAH"}
    },
    {
        "id": "TC-015",
        "name": "Stability Certificate Query",
        "text": "When is it mandatory to renew the stability certificate for a factory building in Gujarat?",
        "site_profile": {"industry_type": "General", "mah_status": "Non_MAH"}
    }
]

def run_tests():
    output_lines = []
    
    header = "="*80 + "\nCOMPLIANCE INTELLIGENCE SYSTEM - EVALUATION REPORT\n" + "="*80
    print(header)
    output_lines.append(header)
    
    results = []
    
    for i, scenario in enumerate(TEST_SCENARIOS):
        print(f"\n[{i+1}/15] {scenario['name']}...")
        
        try:
            start_time = time.time()
            response = requests.post(API_URL, json={
                "query": scenario["text"],
                "site_profile": scenario["site_profile"]
            })
            duration = round(time.time() - start_time, 2)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   SUCCESS ({duration}s)")
                
                results.append({
                    "id": scenario["id"],
                    "name": scenario["name"],
                    "query": scenario["text"],
                    "status": "PASS",
                    "mode": data.get('mode_used', 'N/A'),
                    "topic": data.get('detected_topic', 'N/A'),
                    "duration": duration,
                    "legal_match": data.get('legal_matches')[0]['section_title'] if data.get('legal_matches') else "None",
                    "sar_count": len(data.get('sar_matches', [])),
                    "response": data.get('draft_response', 'No response generated.')
                })
            else:
                print(f"   FAILED: {response.status_code}")
                results.append({"id": scenario["id"], "name": scenario["name"], "status": "FAIL", "error": response.text})
                
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append({"id": scenario["id"], "name": scenario["name"], "status": "ERROR", "error": str(e)})

    # Generate the Detailed File Content
    output_lines.append(f"\nReport Generated On: {time.ctime()}")
    output_lines.append(f"Target API: {API_URL}\n")

    output_lines.append("-" * 80)
    output_lines.append("SUMMARY")
    output_lines.append("-" * 80)
    
    for res in results:
        status_icon = "✅" if res["status"] == "PASS" else "❌"
        output_lines.append(f"{status_icon} {res['id']}: {res['name']} | Time: {res.get('duration', 'N/A')}s | Topic: {res.get('topic', 'N/A')}")

    output_lines.append("\n" + "="*80)
    output_lines.append("DETAILED EVALUATION")
    output_lines.append("="*80)

    for res in results:
        output_lines.append(f"\n[Scenario]: {res['id']} - {res['name']}")
        output_lines.append(f"[Query]: {res.get('query')}")
        
        if res["status"] == "PASS":
            output_lines.append(f"[Intelligence Mode]: {res['mode']}")
            output_lines.append(f"[Primary Legal Reference]: {res['legal_match']}")
            output_lines.append(f"[Similiar Experience Found]: {res['sar_count']} cases")
            output_lines.append("\n[DRAFT COMPLIANCE RESPONSE]:")
            output_lines.append("-" * 40)
            output_lines.append(res['response'])
            output_lines.append("-" * 40)
        else:
            output_lines.append(f"[STATUS]: FAILED")
            output_lines.append(f"[ERROR]: {res.get('error')}")
        
        output_lines.append("\n" + "."*80)

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), "latest_report.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    
    print(f"\n🚀 Evaluation Complete. Detailed report saved to: {output_path}")

if __name__ == "__main__":
    run_tests()
