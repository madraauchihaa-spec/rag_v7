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
    # {
    #     "id": "TC-001",
    #     "text": "Are effective arrangements provided for disposal of wastes and effluents?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-002",
    #     "text": "Are adequate ventilation and temperature control systems maintained?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-003",
    #     "text": "Are dust and fume extraction systems provided and functional?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-004",
    #     "text": "Are drinking water points marked and located away from contamination sources?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-005",
    #     "text": "Are dangerous parts of machinery securely fenced?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-006",
    #     "text": "Are emergency stop mechanisms and interlocks provided and functional on hazardous machines?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-007",
    #     "text": "Is Lockout/Tagout implemented during maintenance and cleaning of machinery?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-008",
    #     "text": "Are lifting machines, chains, ropes and lifting tackles tested and certified periodically by a competent person?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-009",
    #     "text": "Are pressure vessels, boilers and air receivers inspected and certified as per statutory requirements?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-010",
    #     "text": "Are adequate fire-fighting equipment and emergency exits provided and maintained?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-011",
    #     "text": "Is a Safety Officer appointed where required under Section 40B?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-012",
    #     "text": "Is a written Safety Policy prepared and communicated to all workers?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-013",
    #     "text": "Has Site Appraisal Committee approval been obtained for hazardous processes?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-014",
    #     "text": "Are Material Safety Data Sheets (MSDS) available and accessible for hazardous chemicals?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-015",
    #     "text": "Are emergency preparedness and on-site emergency plans documented and periodically tested?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-016",
    #     "text": "Are washing facilities, rest rooms and canteen facilities provided as per number of workers employed?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-017",
    #     "text": "Is a crèche facility provided where more than 30 women workers are employed?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-018",
    #     "text": "Is first aid provided with trained first aiders available in each shift (minimum 1 per 150 workers)?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-019",
    #     "text": "Are working hours, overtime and weekly holidays regulated as per Sections 51–66 of the Act?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-020",
    #     "text": "Is overtime paid at double the ordinary rate of wages?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # },
    # {
    #     "id": "TC-021",
    #     "text": "Are young persons employed only after obtaining a fitness certificate from a Certifying Surgeon?",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # }
    # {
    #     "id": "TC-001",
    #     "text": "what are the requirements of presure plant",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # }
    # {
    #     "id": "TC-001",
    #     "text": "testing of presure vessel",
    #     "site_profile": {"industry_type": "Null", "mah_status": "Null"}
    # }
    # {
    #     "id": "TC-001",
    #     "text": "The main fire exit in the finishing department is blocked by cardboard boxes and scrap material.",
    #     "site_profile": {"industry_type": "Engineering", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-002",
    #     "text": "Electrical panels in the utility area are found unlocked and without rubber mats on the floor.",
    #     "site_profile": {"industry_type": "Textile", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-003",
    #     "text": "A liquid chemical drum is leaking in the storage yard, and there is no secondary containment provided.",
    #     "site_profile": {"industry_type": "Chemical", "mah_status": "MAH"}
    # },
    # {
    #     "id": "TC-004",
    #     "text": "What are the legal requirements for providing first aid boxes based on the number of workers?",
    #     "site_profile": {"industry_type": "Auto Ancillary", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-005",
    #     "text": "Workers were seen working on the roof without a safety harness or a stable lifeline system.",
    #     "site_profile": {"industry_type": "Construction", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-006",
    #     "text": "The rotating parts of the power press machine are exposed and do not have any physical guards.",
    #     "site_profile": {"industry_type": "Engineering", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-007",
    #     "text": "Is there a penalty if the factory license renewal application is submitted after the expiration date?",
    #     "site_profile": {"industry_type": "Agrochemical", "mah_status": "MAH"}
    # },
    # {
    #     "id": "TC-008",
    #     "text": "During site round, it was observed that 50% of the workers in the welding area are not wearing safety goggles.",
    #     "site_profile": {"industry_type": "Fabrication", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-009",
    #     "text": "What as per Factories Act are the standards for ventilation and temperature in the workrooms?",
    #     "site_profile": {"industry_type": "Pharma", "mah_status": "MAH"}
    # },
    # {
    #     "id": "TC-010",
    #     "text": "The air receiver tank in the compressor room has not been hydrostatically tested in the last 2 years.",
    #     "site_profile": {"industry_type": "Chemical", "mah_status": "MAH"}
    # },
    # {
    #     "id": "TC-011",
    #     "text": "The goods lift is used for passenger movement and has no visible stability certificate displayed.",
    #     "site_profile": {"industry_type": "Logistics", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-012",
    #     "text": "What are the rules for providing a canteen and creche facility to female workers?",
    #     "site_profile": {"industry_type": "Food Processing", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-013",
    #     "text": "The smoke detectors in the raw material warehouse are disconnected and showing fault on the panel.",
    #     "site_profile": {"industry_type": "Warehousing", "mah_status": "Non_MAH"}
    # },
    # {
    #     "id": "TC-014",
    #     "text": "Manual handling of 50kg bags is causing ergonomic risks; no mechanical lifting aid is provided.",
    #     "site_profile": {"industry_type": "Fertilizer", "mah_status": "MAH"}
    # },
    # {
    #     "id": "TC-015",
    #     "text": "When is it mandatory to renew the stability certificate for a factory building in Gujarat?",
    #     "site_profile": {"industry_type": "General", "mah_status": "Non_MAH"}
    # }
]

def run_tests():
    output_lines = []
    
    header = "="*80 + "\nCOMPLIANCE INTELLIGENCE SYSTEM - EVALUATION REPORT\n" + "="*80
    print(header)
    output_lines.append(header)
    
    results = []
    
    for i, scenario in enumerate(TEST_SCENARIOS):
        print(f"\n[{i+1}/{len(TEST_SCENARIOS)}] {scenario['id']}...")
        
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
                results.append({"id": scenario["id"], "status": "FAIL", "error": response.text})
                
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append({"id": scenario["id"], "status": "ERROR", "error": str(e)})

    # Generate the Detailed File Content
    output_lines.append(f"\nReport Generated On: {time.ctime()}")
    output_lines.append(f"Target API: {API_URL}\n")

    output_lines.append("-" * 80)
    output_lines.append("SUMMARY")
    output_lines.append("-" * 80)
    
    for res in results:
        status_icon = "✅" if res["status"] == "PASS" else "❌"
        output_lines.append(f"{status_icon} {res['id']} | Time: {res.get('duration', 'N/A')}s | Topic: {res.get('topic', 'N/A')}")

    output_lines.append("\n" + "="*80)
    output_lines.append("DETAILED EVALUATION")
    output_lines.append("="*80)

    for res in results:
        output_lines.append(f"\n[Scenario]: {res['id']}")
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
