from fastapi import FastAPI, Query, Response, status, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# --- DATA MODELS ---

class AppointmentRequest(BaseModel):
    patient_name: str = Field(..., min_length=2)
    doctor_id: int = Field(..., gt=0)
    date: str = Field(..., min_length=8) 
    reason: str = Field(..., min_length=5)
    appointment_type: str = Field("in-person") 
    senior_citizen: bool = Field(False)

class NewDoctor(BaseModel):
    name: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)
    fee: int = Field(..., gt=0)
    experience_years: int = Field(..., gt=0)
    is_available: bool = True

# --- DATABASE ---

doctors = [
    {'id': 1, 'name': 'Dr. Sumith', 'specialization': 'Cardiologist', 'fee': 1000, 'experience_years': 15, 'is_available': True},
    {'id': 2, 'name': 'Dr. Om', 'specialization': 'Dermatologist', 'fee': 800, 'experience_years': 8, 'is_available': True},
    {'id': 3, 'name': 'Dr. Pranay', 'specialization': 'Pediatrician', 'fee': 600, 'experience_years': 12, 'is_available': False},
    {'id': 4, 'name': 'Dr. Rajdeep', 'specialization': 'General', 'fee': 500, 'experience_years': 5, 'is_available': True},
    {'id': 5, 'name': 'Dr. Vinay', 'specialization': 'Cardiologist', 'fee': 1200, 'experience_years': 20, 'is_available': True},
    {'id': 6, 'name': 'Dr. Kaushal', 'specialization': 'Pediatrician', 'fee': 700, 'experience_years': 10, 'is_available': True},
]

appointments = []
appt_counter = 1

# --- HELPER FUNCTIONS ---

def find_doctor(doctor_id: int):
    for d in doctors:
        if d['id'] == doctor_id:
            return d
    return None

def calculate_fee(base_fee: int, appt_type: str, is_senior: bool):
    multiplier = 1.0
    if appt_type.lower() == 'video':
        multiplier = 0.8
    elif appt_type.lower() == 'emergency':
        multiplier = 1.5
    
    final_fee = base_fee * multiplier
    
    if is_senior:
        final_fee = final_fee * 0.85 # 15% Senior discount
        
    return int(final_fee)

# --- DOCTOR ROUTES ---

@app.get('/')
def home():
    return {'message': 'Welcome to MediCare Clinic'}

@app.get('/doctors/summary')
def get_doctors_summary():
    if not doctors:
        return {"message": "No doctors registered"}
    most_exp = max(doctors, key=lambda x: x['experience_years'])
    cheapest = min(doctors, key=lambda x: x['fee'])
    specs = {}
    for d in doctors:
        s = d['specialization']
        specs[s] = specs.get(s, 0) + 1
    return {
        "total_doctors": len(doctors),
        "available_now": len([d for d in doctors if d['is_available']]),
        "veteran_doctor": most_exp['name'],
        "starting_fee": cheapest['fee'],
        "specialization_breakdown": specs
    }

@app.get('/doctors/search')
def search_doctors(keyword: str = Query(..., min_length=1)):
    results = [d for d in doctors if keyword.lower() in d['name'].lower() or keyword.lower() in d['specialization'].lower()]
    if not results:
        return {"message": f"No doctors matching '{keyword}' found.", "results": []}
    return {"total_found": len(results), "results": results}

@app.get('/doctors/sort')
def sort_doctors(sort_by: str = Query('fee'), order: str = Query('asc')):
    if sort_by not in ['fee', 'name', 'experience_years']:
        return {"error": "Invalid sort field"}
    rev = (order == 'desc')
    sorted_docs = sorted(doctors, key=lambda x: x[sort_by], reverse=rev)
    return {"sorted_by": sort_by, "order": order, "data": sorted_docs}

@app.get('/doctors/page')
def paginate_doctors(page: int = Query(1, ge=1), limit: int = Query(3, ge=1)):
    start = (page - 1) * limit
    end = start + limit
    total_pages = -(-len(doctors) // limit)
    return {
        "page": page,
        "total_pages": total_pages,
        "doctors": doctors[start:end]
    }

@app.get('/doctors/browse')
def browse_doctors(
    keyword: str = None,
    sort_by: str = 'fee',
    order: str = 'asc',
    page: int = 1,
    limit: int = 4
):
    data = doctors
    if keyword:
        data = [d for d in data if keyword.lower() in d['name'].lower()]
    rev = (order == 'desc')
    data = sorted(data, key=lambda x: x.get(sort_by, x['fee']), reverse=rev)
    start = (page - 1) * limit
    return {
        "metadata": {"total_found": len(data), "page": page, "total_pages": -(-len(data) // limit)},
        "results": data[start:start+limit]
    }

@app.get('/doctors')
def get_all_doctors():
    return {"total": len(doctors), "doctors": doctors}

@app.get('/doctors/{doctor_id}')
def get_doctor(doctor_id: int):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doc

@app.post('/doctors', status_code=201)
def add_doctor(doc_in: NewDoctor):
    if any(d['name'].lower() == doc_in.name.lower() for d in doctors):
        raise HTTPException(status_code=400, detail="Doctor name already exists")
    new_id = max(d['id'] for d in doctors) + 1
    new_doc = {"id": new_id, **doc_in.dict()}
    doctors.append(new_doc)
    return new_doc

@app.put('/doctors/{doctor_id}')
def update_doctor(doctor_id: int, fee: Optional[int] = None, is_available: Optional[bool] = None):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if fee is not None: doc['fee'] = fee
    if is_available is not None: doc['is_available'] = is_available
    return doc

@app.delete('/doctors/{doctor_id}')
def delete_doctor(doctor_id: int):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    active_appt = [a for a in appointments if a['doctor_id'] == doctor_id and a['status'] == 'scheduled']
    if active_appt:
        return {"error": "Cannot delete doctor with active scheduled appointments"}
    doctors.remove(doc)
    return {"message": f"Doctor {doctor_id} removed successfully"}

# --- APPOINTMENT ROUTES ---

@app.get('/appointments/active')
def get_active_appointments():
    active = [a for a in appointments if a['status'] in ['scheduled', 'confirmed']]
    return {"total": len(active), "appointments": active}

@app.get('/appointments/search')
def search_appointments(patient_name: str = Query(..., min_length=1)):
    results = [a for a in appointments if patient_name.lower() in a['patient_name'].lower()]
    return {"total_found": len(results), "results": results}

@app.get('/appointments/sort')
def sort_appointments(sort_by: str = Query('final_fee'), order: str = Query('asc')):
    if sort_by not in ['final_fee', 'date']:
        return {"error": "Can only sort by 'final_fee' or 'date'"}
    rev = (order == 'desc')
    return sorted(appointments, key=lambda x: x.get(sort_by), reverse=rev)

@app.get('/appointments/page')
def page_appointments(page: int = Query(1, ge=1), limit: int = Query(5, ge=1)):
    start = (page - 1) * limit
    total_pages = -(-len(appointments) // limit) if appointments else 0
    return {"page": page, "total_pages": total_pages, "results": appointments[start:start+limit]}

@app.get('/appointments/by-doctor/{doctor_id}')
def appts_by_doctor(doctor_id: int):
    return [a for a in appointments if a['doctor_id'] == doctor_id]

@app.get('/appointments')
def get_all_appointments():
    return {"total": len(appointments), "appointments": appointments}

@app.post('/appointments')
def book_appointment(req: AppointmentRequest):
    global appt_counter
    doc = find_doctor(req.doctor_id)
    if not doc: return {"error": "Doctor not found"}
    if not doc['is_available']: return {"error": f"{doc['name']} is not available"}
    
    fee = calculate_fee(doc['fee'], req.appointment_type, req.senior_citizen)
    new_appt = {
        "appointment_id": appt_counter, "patient_name": req.patient_name,
        "doctor_id": doc['id'], "doctor_name": doc['name'], "date": req.date,
        "type": req.appointment_type, "final_fee": fee, "status": "scheduled"
    }
    appointments.append(new_appt)
    appt_counter += 1
    return new_appt

# --- WORKFLOW ROUTES ---

@app.post('/appointments/{appt_id}/confirm')
def confirm_appt(appt_id: int):
    for a in appointments:
        if a['appointment_id'] == appt_id:
            a['status'] = 'confirmed'
            return a
    return {"error": "Not found"}

@app.post('/appointments/{appt_id}/cancel')
def cancel_appt(appt_id: int):
    for a in appointments:
        if a['appointment_id'] == appt_id:
            a['status'] = 'cancelled'
            doc = find_doctor(a['doctor_id'])
            if doc: doc['is_available'] = True
            return a
    return {"error": "Not found"}

@app.post('/appointments/{appt_id}/complete')
def complete_appt(appt_id: int):
    for a in appointments:
        if a['appointment_id'] == appt_id:
            a['status'] = 'completed'
            return a
    return {"error": "Not found"}