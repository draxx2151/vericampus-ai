import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

from . import config
from .quality_degradations import apply_quality_degradation, compute_ground_truth_metrics


def _draw_watermark(image: Image.Image, text: str) -> Image.Image:
    watermark_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)
    font = ImageFont.load_default()
    
    text_color = (200, 200, 200, 128)
    width, height = image.size
    
    for y in range(0, height, 150):
        for x in range(0, width, 250):
            draw.text((x, y), text, fill=text_color, font=font)
            
    watermark_layer = watermark_layer.rotate(45, center=(width // 2, height // 2))
    
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    out = Image.alpha_composite(image, watermark_layer)
    return out.convert('RGB')


def _create_base_image(border_style: int = 0) -> Tuple[Image.Image, ImageDraw.ImageDraw, any]:
    image = Image.new('RGB', (config.IMAGE_WIDTH, config.IMAGE_HEIGHT), color=config.BG_COLOR)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    
    if border_style == 1:
        # Double border
        draw.rectangle([18, 18, config.IMAGE_WIDTH - 18, config.IMAGE_HEIGHT - 18], outline=config.BORDER_COLOR, width=3)
        draw.rectangle([25, 25, config.IMAGE_WIDTH - 25, config.IMAGE_HEIGHT - 25], outline=config.ACCENT_COLOR, width=1)
    elif border_style == 2:
        # Header banner style border
        draw.rectangle([20, 20, config.IMAGE_WIDTH - 20, config.IMAGE_HEIGHT - 20], outline=config.BORDER_COLOR, width=2)
        draw.rectangle([20, 20, config.IMAGE_WIDTH - 20, 110], fill=(240, 245, 250), outline=config.BORDER_COLOR, width=2)
    else:
        # Standard formal rectangle
        draw.rectangle([20, 20, config.IMAGE_WIDTH - 20, config.IMAGE_HEIGHT - 20], outline=config.BORDER_COLOR, width=4)
        
    return image, draw, font


def _draw_field(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str, font: any) -> Tuple[int, int, int, int]:
    text = f"{label}: {value}"
    bbox = draw.textbbox((x, y), text, font=font)
    draw.text((x, y), text, fill=config.TEXT_COLOR, font=font)
    return bbox


def render_government_id(student: dict, layout_variant: int = 0) -> Tuple[Image.Image, dict, dict]:
    border_style = layout_variant % 3
    image, draw, font = _create_base_image(border_style)
    
    bboxes = {}
    ground_truth = {
        'id_type': student['id_type'],
        'id_number': student['id_number'],
        'full_name': student['full_name'],
        'date_of_birth': student['date_of_birth'],
        'gender': student['gender'],
        'address': student['address']
    }

    if layout_variant == 1:
        # Variant 1: Photo box on right, compact personal card format
        y = 50
        draw.text((220, y), "GOVERNMENT OF INDIA", fill=config.ACCENT_COLOR, font=font)
        y += 35
        draw.text((220, y), f"UNIQUE IDENTIFICATION AUTHORITY OF INDIA ({student['id_type'].upper()})", fill=config.TEXT_COLOR, font=font)
        
        # Photo placeholder box
        draw.rectangle([540, 140, 690, 330], outline=config.BORDER_COLOR, width=2)
        draw.text((585, 225), "[ PHOTO ]", fill=(100, 100, 100), font=font)
        
        y = 150
        x = 50
        bboxes['id_type'] = _draw_field(draw, x, y, "Document Type", student['id_type'], font)
        y += 40
        bboxes['id_number'] = _draw_field(draw, x, y, "Identification No", student['id_number'], font)
        y += 40
        bboxes['full_name'] = _draw_field(draw, x, y, "Name of Holder", student['full_name'], font)
        y += 40
        bboxes['date_of_birth'] = _draw_field(draw, x, y, "DOB", student['date_of_birth'], font)
        y += 40
        bboxes['gender'] = _draw_field(draw, x, y, "Sex", student['gender'], font)
        y += 50
        bboxes['address'] = _draw_field(draw, x, y, "Permanent Address", student['address'], font)
    elif layout_variant == 2:
        # Variant 2: Emblem header badge card
        draw.ellipse([365, 35, 435, 105], outline=config.ACCENT_COLOR, width=3)
        draw.text((380, 62), "INDIA", fill=config.ACCENT_COLOR, font=font)
        y = 120
        draw.text((config.IMAGE_WIDTH // 3, y), "GOVERNMENT OF INDIA", fill=config.ACCENT_COLOR, font=font)
        y += 30
        draw.text((config.IMAGE_WIDTH // 3, y), student['id_type'].upper(), fill=config.TEXT_COLOR, font=font)
        draw.line([(50, 190), (config.IMAGE_WIDTH - 50, 190)], fill=config.ACCENT_COLOR, width=2)
        
        y = 210
        x = 60
        bboxes['id_type'] = _draw_field(draw, x, y, "ID Category", student['id_type'], font)
        y += 42
        bboxes['id_number'] = _draw_field(draw, x, y, "Identity Card No", student['id_number'], font)
        y += 42
        bboxes['full_name'] = _draw_field(draw, x, y, "Full Legal Name", student['full_name'], font)
        y += 42
        bboxes['date_of_birth'] = _draw_field(draw, x, y, "Date of Birth", student['date_of_birth'], font)
        y += 42
        bboxes['gender'] = _draw_field(draw, x, y, "Gender", student['gender'], font)
        y += 42
        bboxes['address'] = _draw_field(draw, x, y, "Residential Address", student['address'], font)
    else:
        # Variant 0: Standard centered header format
        y = 50
        draw.text((config.IMAGE_WIDTH // 3, y), "GOVERNMENT OF INDIA", fill=config.ACCENT_COLOR, font=font)
        y += 40
        draw.text((config.IMAGE_WIDTH // 3, y), student['id_type'].upper(), fill=config.TEXT_COLOR, font=font)
        y += 60
        x = 50
        bboxes['id_type'] = _draw_field(draw, x, y, "ID Type", student['id_type'], font)
        y += 40
        bboxes['id_number'] = _draw_field(draw, x, y, "ID Number", student['id_number'], font)
        y += 40
        bboxes['full_name'] = _draw_field(draw, x, y, "Full Name", student['full_name'], font)
        y += 40
        bboxes['date_of_birth'] = _draw_field(draw, x, y, "Date of Birth", student['date_of_birth'], font)
        y += 40
        bboxes['gender'] = _draw_field(draw, x, y, "Gender", student['gender'], font)
        y += 40
        bboxes['address'] = _draw_field(draw, x, y, "Address", student['address'], font)
    
    image = _draw_watermark(image, config.WATERMARK_TEXT)
    return image, ground_truth, bboxes


def render_marksheet(student: dict, layout_variant: int = 0) -> Tuple[Image.Image, dict, dict]:
    border_style = layout_variant % 3
    image, draw, font = _create_base_image(border_style)
    
    bboxes = {}
    ground_truth = {
        'candidate_name': student['full_name'],
        'roll_number': student['roll_number'],
        'exam_name': student['exam_name'],
        'passing_year': str(student['passing_year']),
        'total_marks': str(student['total_marks']),
        'max_marks': str(student['max_marks']),
        'percentage': f"{student['percentage']:.2f}",
        'result_status': student['result_status']
    }

    if layout_variant == 1:
        # Variant 1: Tabular grid format with subject marks rows
        y = 45
        draw.text((180, y), "MAHARASHTRA STATE BOARD OF SECONDARY & HIGHER SECONDARY EDUCATION", fill=config.ACCENT_COLOR, font=font)
        y += 30
        draw.text((250, y), "STATEMENT OF MARKS & GRADES", fill=config.TEXT_COLOR, font=font)
        y += 40
        
        bboxes['candidate_name'] = _draw_field(draw, 50, y, "Candidate Name", student['full_name'], font)
        bboxes['roll_number'] = _draw_field(draw, 450, y, "Seat/Roll No", student['roll_number'], font)
        y += 35
        bboxes['exam_name'] = _draw_field(draw, 50, y, "Examination", student['exam_name'], font)
        bboxes['passing_year'] = _draw_field(draw, 450, y, "Year of Exam", str(student['passing_year']), font)
        y += 45
        
        # Draw tabular grid
        table_top = y
        draw.rectangle([50, table_top, 720, table_top + 280], outline=config.BORDER_COLOR, width=2)
        # Header row
        draw.rectangle([50, table_top, 720, table_top + 35], fill=(235, 240, 245), outline=config.BORDER_COLOR, width=1)
        draw.text((60, table_top + 10), "Subject Description", fill=config.TEXT_COLOR, font=font)
        draw.text((360, table_top + 10), "Max Marks", fill=config.TEXT_COLOR, font=font)
        draw.text((490, table_top + 10), "Marks Obtained", fill=config.TEXT_COLOR, font=font)
        draw.text((640, table_top + 10), "Remarks", fill=config.TEXT_COLOR, font=font)
        
        subjects = ["English Compulsory", "Mathematics & Statistics", "Physics / Science", "Chemistry / Social Sciences", "Information Technology"]
        sub_y = table_top + 45
        for s_idx, subj in enumerate(subjects):
            draw.text((60, sub_y), subj, fill=config.TEXT_COLOR, font=font)
            draw.text((380, sub_y), "100", fill=config.TEXT_COLOR, font=font)
            draw.text((510, sub_y), "75", fill=config.TEXT_COLOR, font=font)
            draw.text((645, sub_y), "PASS", fill=config.TEXT_COLOR, font=font)
            draw.line([(50, sub_y + 25), (720, sub_y + 25)], fill=(200, 200, 200), width=1)
            sub_y += 35
            
        # Vertical column dividers
        draw.line([(340, table_top), (340, table_top + 280)], fill=config.BORDER_COLOR, width=1)
        draw.line([(470, table_top), (470, table_top + 280)], fill=config.BORDER_COLOR, width=1)
        draw.line([(620, table_top), (620, table_top + 280)], fill=config.BORDER_COLOR, width=1)
        
        y = table_top + 300
        bboxes['total_marks'] = _draw_field(draw, 50, y, "Total Marks Secured", str(student['total_marks']), font)
        bboxes['max_marks'] = _draw_field(draw, 450, y, "Total Max Marks", str(student['max_marks']), font)
        y += 40
        bboxes['percentage'] = _draw_field(draw, 50, y, "Aggregate Percentage", f"{student['percentage']:.2f}%", font)
        bboxes['result_status'] = _draw_field(draw, 450, y, "Final Result", student['result_status'], font)
    elif layout_variant == 2:
        # Variant 2: University / College transcript format
        y = 50
        draw.text((220, y), "UNIVERSITY OF PUNE / MUMBAI ACADEMIC COUNCIL", fill=config.ACCENT_COLOR, font=font)
        y += 35
        draw.text((250, y), "OFFICIAL TRANSCRIPT & PERFORMANCE RECORD", fill=config.TEXT_COLOR, font=font)
        y += 50
        x = 55
        bboxes['candidate_name'] = _draw_field(draw, x, y, "Student Name", student['full_name'], font)
        y += 38
        bboxes['roll_number'] = _draw_field(draw, x, y, "Registration / PRN No", student['roll_number'], font)
        y += 38
        bboxes['exam_name'] = _draw_field(draw, x, y, "Course / Degree", student['exam_name'], font)
        y += 38
        bboxes['passing_year'] = _draw_field(draw, x, y, "Year of Convocation", str(student['passing_year']), font)
        y += 38
        bboxes['total_marks'] = _draw_field(draw, x, y, "Marks Obtained", str(student['total_marks']), font)
        y += 38
        bboxes['max_marks'] = _draw_field(draw, x, y, "Maximum Marks", str(student['max_marks']), font)
        y += 38
        bboxes['percentage'] = _draw_field(draw, x, y, "Percentage", f"{student['percentage']:.2f}", font)
        y += 38
        bboxes['result_status'] = _draw_field(draw, x, y, "Class Awarded", student['result_status'], font)
    else:
        # Variant 0: Standard vertical format
        y = 50
        draw.text((config.IMAGE_WIDTH // 4, y), "MAHARASHTRA STATE BOARD OF EXAMINATION", fill=config.ACCENT_COLOR, font=font)
        y += 40
        draw.text((config.IMAGE_WIDTH // 3, y), student['exam_name'].upper(), fill=config.TEXT_COLOR, font=font)
        y += 60
        x = 50
        bboxes['candidate_name'] = _draw_field(draw, x, y, "Candidate Name", student['full_name'], font)
        y += 40
        bboxes['roll_number'] = _draw_field(draw, x, y, "Roll Number", student['roll_number'], font)
        y += 40
        bboxes['exam_name'] = _draw_field(draw, x, y, "Exam Name", student['exam_name'], font)
        y += 40
        bboxes['passing_year'] = _draw_field(draw, x, y, "Passing Year", str(student['passing_year']), font)
        y += 40
        bboxes['total_marks'] = _draw_field(draw, x, y, "Total Marks", str(student['total_marks']), font)
        y += 40
        bboxes['max_marks'] = _draw_field(draw, x, y, "Maximum Marks", str(student['max_marks']), font)
        y += 40
        bboxes['percentage'] = _draw_field(draw, x, y, "Percentage", f"{student['percentage']:.2f}", font)
        y += 40
        bboxes['result_status'] = _draw_field(draw, x, y, "Result", student['result_status'], font)

    image = _draw_watermark(image, config.WATERMARK_TEXT)
    return image, ground_truth, bboxes


def render_income_certificate(student: dict, layout_variant: int = 0) -> Tuple[Image.Image, dict, dict]:
    border_style = layout_variant % 3
    image, draw, font = _create_base_image(border_style)
    
    bboxes = {}
    ground_truth = {
        'applicant_name': student['full_name'],
        'father_guardian_name': student['father_guardian_name'],
        'annual_income_inr': str(student['annual_income_inr']),
        'certificate_number': student['income_certificate_number'],
        'issuing_authority': student['issuing_authority'],
        'issue_date': student['issue_date'],
        'financial_year': student['financial_year']
    }

    if layout_variant == 1:
        # Variant 1: Formal legal proclamation with seal and signature block
        y = 50
        draw.text((250, y), "GOVERNMENT OF MAHARASHTRA", fill=config.ACCENT_COLOR, font=font)
        y += 30
        draw.text((230, y), "REVENUE AND FOREST DEPARTMENT", fill=config.TEXT_COLOR, font=font)
        y += 35
        draw.text((270, y), "CERTIFICATE OF ANNUAL INCOME", fill=config.TEXT_COLOR, font=font)
        y += 50
        
        # Proclamation prose
        prose_lines = [
            f"This is to solemnly certify that {student['full_name']}, son/daughter of",
            f"{student['father_guardian_name']}, residing at Maharashtra state,",
            f"has an annual family income from all revenue sources evaluated at",
            f"INR {student['annual_income_inr']}/- for the financial assessment year {student['financial_year']}.",
            "This certificate is verified pursuant to Maharashtra Revenue Act provisions."
        ]
        x = 55
        for line in prose_lines:
            draw.text((x, y), line, fill=config.TEXT_COLOR, font=font)
            y += 30
            
        y += 40
        bboxes['applicant_name'] = _draw_field(draw, x, y, "Applicant Name", student['full_name'], font)
        y += 35
        bboxes['father_guardian_name'] = _draw_field(draw, x, y, "Father's Name", student['father_guardian_name'], font)
        y += 35
        bboxes['annual_income_inr'] = _draw_field(draw, x, y, "Total Income (INR)", str(student['annual_income_inr']), font)
        y += 35
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate No", student['income_certificate_number'], font)
        y += 35
        bboxes['issuing_authority'] = _draw_field(draw, x, y, "Issuing Officer", student['issuing_authority'], font)
        y += 35
        bboxes['issue_date'] = _draw_field(draw, x, y, "Date of Issuance", student['issue_date'], font)
        bboxes['financial_year'] = (x, y, x + 200, y + 20)
        
        # Official Seal and Signature block at bottom
        draw.ellipse([80, y + 60, 180, y + 160], outline=config.ACCENT_COLOR, width=2)
        draw.text((105, y + 105), "[ REVENUE SEAL ]", fill=config.ACCENT_COLOR, font=font)
        draw.text((500, y + 110), "Sd/- Tehsildar / Competent Authority", fill=config.TEXT_COLOR, font=font)
    elif layout_variant == 2:
        # Variant 2: e-District revenue portal layout with application ID box
        draw.rectangle([500, 35, 720, 95], outline=config.BORDER_COLOR, width=1)
        draw.text((515, 50), f"Bar Code / Ref ID", fill=(100, 100, 100), font=font)
        draw.text((515, 70), student['income_certificate_number'], fill=config.TEXT_COLOR, font=font)
        
        y = 50
        draw.text((120, y), "GOVERNMENT OF MAHARASHTRA", fill=config.ACCENT_COLOR, font=font)
        y += 30
        draw.text((120, y), "MAHASAVA DIGITAL CITIZEN SERVICES", fill=config.TEXT_COLOR, font=font)
        y += 50
        x = 55
        bboxes['applicant_name'] = _draw_field(draw, x, y, "Applicant Name", student['full_name'], font)
        y += 38
        bboxes['father_guardian_name'] = _draw_field(draw, x, y, "Father / Guardian", student['father_guardian_name'], font)
        y += 38
        bboxes['annual_income_inr'] = _draw_field(draw, x, y, "Annual Income (INR)", str(student['annual_income_inr']), font)
        y += 38
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate Number", student['income_certificate_number'], font)
        y += 38
        bboxes['issuing_authority'] = _draw_field(draw, x, y, "Issuing Authority", student['issuing_authority'], font)
        y += 38
        bboxes['issue_date'] = _draw_field(draw, x, y, "Issue Date", student['issue_date'], font)
        y += 38
        bboxes['financial_year'] = _draw_field(draw, x, y, "Financial Year", student['financial_year'], font)
    else:
        # Variant 0: Standard vertical layout
        y = 50
        draw.text((config.IMAGE_WIDTH // 3, y), "GOVERNMENT OF MAHARASHTRA", fill=config.ACCENT_COLOR, font=font)
        y += 40
        draw.text((config.IMAGE_WIDTH // 3, y), "INCOME CERTIFICATE", fill=config.TEXT_COLOR, font=font)
        y += 60
        x = 50
        bboxes['applicant_name'] = _draw_field(draw, x, y, "Applicant Name", student['full_name'], font)
        y += 40
        bboxes['father_guardian_name'] = _draw_field(draw, x, y, "Father/Guardian Name", student['father_guardian_name'], font)
        y += 40
        bboxes['annual_income_inr'] = _draw_field(draw, x, y, "Annual Income (INR)", str(student['annual_income_inr']), font)
        y += 40
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate Number", student['income_certificate_number'], font)
        y += 40
        bboxes['issuing_authority'] = _draw_field(draw, x, y, "Issuing Authority", student['issuing_authority'], font)
        y += 40
        bboxes['issue_date'] = _draw_field(draw, x, y, "Issue Date", student['issue_date'], font)
        y += 40
        bboxes['financial_year'] = _draw_field(draw, x, y, "Financial Year", student['financial_year'], font)

    image = _draw_watermark(image, config.WATERMARK_TEXT)
    return image, ground_truth, bboxes


def render_domicile_certificate(student: dict, layout_variant: int = 0) -> Tuple[Image.Image, dict, dict]:
    border_style = layout_variant % 3
    image, draw, font = _create_base_image(border_style)
    
    bboxes = {}
    ground_truth = {
        'candidate_name': student['full_name'],
        'state': student['state'],
        'is_maharashtra_domicile': str(student['is_maharashtra_domicile']),
        'certificate_number': student['domicile_certificate_number'],
        'issue_date': student['issue_date']
    }

    if layout_variant == 1:
        # Variant 1: Executive Magistrate format
        y = 50
        draw.text((230, y), "OFFICE OF THE EXECUTIVE MAGISTRATE", fill=config.ACCENT_COLOR, font=font)
        y += 30
        draw.text((220, y), "GOVERNMENT OF MAHARASHTRA DISTRICT COURT", fill=config.TEXT_COLOR, font=font)
        y += 35
        draw.text((230, y), "CERTIFICATE OF AGE, NATIONALITY AND DOMICILE", fill=config.TEXT_COLOR, font=font)
        y += 50
        x = 55
        declaration_text = [
            f"Whereas an application has been made by {student['full_name']}",
            "satisfactorily establishing permanent residency in Maharashtra.",
            "It is hereby certified that the candidate is a bona fide resident",
            f"of the State of {student['state']} and satisfies all legal criteria."
        ]
        for line in declaration_text:
            draw.text((x, y), line, fill=config.TEXT_COLOR, font=font)
            y += 30
            
        y += 35
        bboxes['candidate_name'] = _draw_field(draw, x, y, "Name of Domicile", student['full_name'], font)
        y += 38
        bboxes['state'] = _draw_field(draw, x, y, "Domiciled State", student['state'], font)
        y += 38
        bboxes['is_maharashtra_domicile'] = _draw_field(draw, x, y, "Maharashtra Resident", str(student['is_maharashtra_domicile']), font)
        y += 38
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate / Registration No", student['domicile_certificate_number'], font)
        y += 38
        bboxes['issue_date'] = _draw_field(draw, x, y, "Date of Verification", student['issue_date'], font)
    elif layout_variant == 2:
        # Variant 2: Digital e-Certificate with simulated QR code box
        draw.rectangle([550, 45, 680, 175], outline=config.BORDER_COLOR, width=2)
        draw.text((580, 105), "[ QR CODE ]", fill=(100, 100, 100), font=font)
        y = 50
        draw.text((120, y), "MAHARASHTRA CITIZEN SERVICES PORTAL", fill=config.ACCENT_COLOR, font=font)
        y += 35
        draw.text((120, y), "DOMICILE / PERMANENT RESIDENCE CERTIFICATE", fill=config.TEXT_COLOR, font=font)
        y += 75
        x = 60
        bboxes['candidate_name'] = _draw_field(draw, x, y, "Candidate Name", student['full_name'], font)
        y += 40
        bboxes['state'] = _draw_field(draw, x, y, "State of Domicile", student['state'], font)
        y += 40
        bboxes['is_maharashtra_domicile'] = _draw_field(draw, x, y, "Is Maharashtra Domicile", str(student['is_maharashtra_domicile']), font)
        y += 40
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate No", student['domicile_certificate_number'], font)
        y += 40
        bboxes['issue_date'] = _draw_field(draw, x, y, "Date of Issue", student['issue_date'], font)
    else:
        # Variant 0: Standard vertical layout
        y = 50
        draw.text((config.IMAGE_WIDTH // 3, y), "GOVERNMENT OF MAHARASHTRA", fill=config.ACCENT_COLOR, font=font)
        y += 40
        draw.text((config.IMAGE_WIDTH // 3, y), "DOMICILE CERTIFICATE", fill=config.TEXT_COLOR, font=font)
        y += 60
        x = 50
        bboxes['candidate_name'] = _draw_field(draw, x, y, "Candidate Name", student['full_name'], font)
        y += 40
        bboxes['state'] = _draw_field(draw, x, y, "State", student['state'], font)
        y += 40
        bboxes['is_maharashtra_domicile'] = _draw_field(draw, x, y, "Is Maharashtra Domicile", str(student['is_maharashtra_domicile']), font)
        y += 40
        bboxes['certificate_number'] = _draw_field(draw, x, y, "Certificate Number", student['domicile_certificate_number'], font)
        y += 40
        bboxes['issue_date'] = _draw_field(draw, x, y, "Issue Date", student['issue_date'], font)

    image = _draw_watermark(image, config.WATERMARK_TEXT)
    return image, ground_truth, bboxes


def render_unknown_document(index: int, variant: Optional[str] = None) -> Tuple[Image.Image, dict, dict]:
    """
    Renders a synthetic UNKNOWN / OTHER document representation:
    - blank_paper: Mostly empty canvas with faint header note
    - generic_letter: Formal administrative correspondence letter
    - unrelated_receipt: Supermarket store checkout receipt
    - generic_form: Recreational gym/sports membership form
    """
    types = config.UNKNOWN_DOCUMENT_TYPES
    sub_type = variant or types[index % len(types)]
    
    image = Image.new('RGB', (config.IMAGE_WIDTH, config.IMAGE_HEIGHT), color=(252, 252, 252))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    bboxes = {}
    ground_truth = {"document_type": "UNKNOWN", "sub_type": sub_type}

    if sub_type == "blank_paper":
        # Nearly blank page with subtle corner boundary and small handwritten note
        draw.rectangle([30, 30, config.IMAGE_WIDTH - 30, config.IMAGE_HEIGHT - 30], outline=(220, 220, 220), width=1)
        draw.text((80, 80), "MEMORANDUM / SCRATCH PAD", fill=(180, 180, 180), font=font)
        draw.line([(80, 140), (400, 140)], fill=(230, 230, 230), width=1)
        draw.line([(80, 180), (350, 180)], fill=(230, 230, 230), width=1)
    elif sub_type == "generic_letter":
        # Formal letter with sender/recipient and correspondence body
        draw.text((60, 50), "APEX BUSINESS CONSULTING SERVICES", fill=(50, 50, 50), font=font)
        draw.text((60, 75), "Commercial Tower B, Nariman Point, Mumbai", fill=(100, 100, 100), font=font)
        draw.line([(60, 105), (config.IMAGE_WIDTH - 60, 105)], fill=(150, 150, 150), width=1)
        
        draw.text((60, 140), "To: Operations Department", fill=(40, 40, 40), font=font)
        draw.text((60, 165), "Subject: Update Regarding Monthly Supplies Request", fill=(40, 40, 40), font=font)
        
        paragraphs = [
            "Dear Sir/Madam,",
            "Please be advised that the quarterly logistics procurement has been",
            "reviewed and authorized according to standard commercial schedules.",
            "All inventory items mentioned in schedule B will be dispatched to",
            "the regional distribution hub within the forthcoming billing cycle.",
            "Kindly acknowledge receipt of this memorandum upon arrival.",
            "",
            "Sincerely,",
            "Procurement Division Lead"
        ]
        y = 210
        for p in paragraphs:
            draw.text((60, y), p, fill=(40, 40, 40), font=font)
            y += 28
    elif sub_type == "unrelated_receipt":
        # Retail store POS invoice
        draw.rectangle([100, 40, config.IMAGE_WIDTH - 100, config.IMAGE_HEIGHT - 100], outline=(180, 180, 180), width=1)
        draw.text((280, 70), "SUPER VALUE SUPERMARKET", fill=(20, 20, 20), font=font)
        draw.text((310, 95), "TAX INVOICE / CASH BILL", fill=(80, 80, 80), font=font)
        draw.line([(120, 130), (config.IMAGE_WIDTH - 120, 130)], fill=(180, 180, 180), width=1)
        
        draw.text((120, 150), "Date: 14-Aug-2026", fill=(40, 40, 40), font=font)
        draw.text((450, 150), "Cashier: Register #04", fill=(40, 40, 40), font=font)
        draw.text((120, 180), "Item Description             Qty    Price     Amount", fill=(30, 30, 30), font=font)
        draw.line([(120, 205), (config.IMAGE_WIDTH - 120, 205)], fill=(180, 180, 180), width=1)
        
        items = [
            ("A4 Notebook 200 Pages", "2", "80.00", "160.00"),
            ("Ballpoint Pens (Pack of 5)", "1", "50.00", "50.00"),
            ("Wireless Optical Mouse", "1", "450.00", "450.00"),
            ("USB-C Charging Cable", "1", "199.00", "199.00"),
            ("Sticky Notes Memo Pad", "3", "30.00", "90.00"),
        ]
        y = 220
        for desc, qty, rate, amt in items:
            draw.text((120, y), f"{desc:<28} {qty:<6} {rate:<9} {amt}", fill=(40, 40, 40), font=font)
            y += 30
            
        draw.line([(120, y + 20), (config.IMAGE_WIDTH - 120, y + 20)], fill=(180, 180, 180), width=1)
        y += 35
        draw.text((120, y), "Subtotal: INR 949.00", fill=(40, 40, 40), font=font)
        y += 25
        draw.text((120, y), "CGST (9%) + SGST (9%): INR 170.82", fill=(40, 40, 40), font=font)
        y += 25
        draw.text((120, y), "NET TOTAL PAID: INR 1119.82", fill=(20, 20, 20), font=font)
    else:
        # generic_form: Recreational club membership
        draw.rectangle([40, 40, config.IMAGE_WIDTH - 40, config.IMAGE_HEIGHT - 40], outline=config.BORDER_COLOR, width=2)
        draw.text((220, 65), "COMMUNITY ATHLETIC CLUB — REGISTRATION FORM", fill=config.ACCENT_COLOR, font=font)
        draw.line([(50, 95), (config.IMAGE_WIDTH - 50, 95)], fill=config.BORDER_COLOR, width=1)
        
        fields = [
            "Applicant Name: ___________________________",
            "Emergency Contact Phone: ___________________",
            "Membership Category: [ ] Individual  [ ] Family  [ ] Student",
            "Preferred Activities: [ ] Swimming  [ ] Tennis   [ ] Fitness Center",
            "Health Declaration: I confirm I am physically fit for sports.",
            "Signature of Applicant: _____________________  Date: __________"
        ]
        y = 140
        for f in fields:
            draw.text((60, y), f, fill=(30, 30, 30), font=font)
            y += 50

    # Ensure synthetic watermark is consistently applied across UNKNOWN documents
    image = _draw_watermark(image, config.WATERMARK_TEXT)
    return image, ground_truth, bboxes


def generate_document_image(
    student: dict,
    doc_type: str,
    quality_label: Optional[str] = None,
    layout_variant: int = 0,
) -> Tuple[Image.Image, dict, dict, dict]:
    """
    Renders document and applies quality degradation.
    Returns: (PIL Image, ground_truth_fields, bounding_boxes, quality_metrics)
    """
    dt = doc_type.lower()
    if dt == "government_id":
        base_img, gt, bboxes = render_government_id(student, layout_variant=layout_variant)
    elif dt == "marksheet":
        base_img, gt, bboxes = render_marksheet(student, layout_variant=layout_variant)
    elif dt == "income_certificate":
        base_img, gt, bboxes = render_income_certificate(student, layout_variant=layout_variant)
    elif dt == "domicile_certificate":
        base_img, gt, bboxes = render_domicile_certificate(student, layout_variant=layout_variant)
    elif dt == "unknown":
        idx = student.get("student_id", 0) if isinstance(student, dict) else 0
        base_img, gt, bboxes = render_unknown_document(index=idx)
    else:
        raise ValueError(f"Unknown document type: {doc_type}")

    # Convert PIL Image to cv2 BGR
    img_bgr = cv2.cvtColor(np.array(base_img), cv2.COLOR_RGB2BGR)

    target_label = quality_label or "HIGH"
    degraded_bgr, quality_metrics = apply_quality_degradation(img_bgr, target_label)

    # Convert back to PIL Image (RGB)
    degraded_rgb = cv2.cvtColor(degraded_bgr, cv2.COLOR_BGR2RGB)
    final_img = Image.fromarray(degraded_rgb)

    return final_img, gt, bboxes, quality_metrics


def generate_all_documents(
    students: list[dict],
    output_dir: Path,
) -> list[dict]:
    """
    Generate all 4 document images for each student with layout and quality variations,
    plus synthetic UNKNOWN/OTHER class images.
    Saves PNGs to output_dir/images/{doc_type}/student_{id}_{doc_type}.png
    Returns list of metadata dicts with ground truth, classification label, and quality indicators.
    """
    metadata_list = []
    
    for doc_type in config.ALL_CLASSIFICATION_CLASSES:
        (output_dir / "images" / doc_type).mkdir(parents=True, exist_ok=True)

    # Balanced pool representing target distribution:
    # 35% HIGH, 35% MEDIUM, 18% LOW, 12% UNREADABLE
    quality_pool = [
        "HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW", "UNREADABLE",
        "HIGH", "MEDIUM", "HIGH", "MEDIUM", "LOW", "HIGH"
    ]
        
    for student in students:
        student_id = student['student_id']
        for doc_idx, doc_type in enumerate(config.DOCUMENT_TYPES):
            # Deterministic, balanced quality assignment per (student_id, doc_type)
            pool_idx = (student_id * 7 + doc_idx * 3) % len(quality_pool)
            target_quality = quality_pool[pool_idx]
            layout_variant = (student_id + doc_idx) % 3

            img, gt, bboxes, q_metrics = generate_document_image(
                student=student,
                doc_type=doc_type,
                quality_label=target_quality,
                layout_variant=layout_variant,
            )
            
            filename = f"student_{student_id}_{doc_type}.png"
            filepath = output_dir / "images" / doc_type / filename
            
            img.save(filepath)
            
            metadata_list.append({
                "student_id": student_id,
                "doc_type": doc_type,
                "filepath": str(filepath.relative_to(output_dir)),
                "ground_truth": gt,
                "bounding_boxes": bboxes,
                "quality_metrics": q_metrics,
                "quality_label": q_metrics["quality_label"],
                "quality_score": q_metrics["quality_score"],
            })

    # Generate synthetic UNKNOWN / OTHER class images
    unknown_types = config.UNKNOWN_DOCUMENT_TYPES
    # Generate 8 unknown documents (2 of each unknown subtype)
    for u_idx in range(8):
        sub_type = unknown_types[u_idx % len(unknown_types)]
        u_student_id = 9000 + u_idx
        fake_student = {"student_id": u_student_id, "sub_type": sub_type}
        
        base_img, gt, bboxes = render_unknown_document(index=u_idx, variant=sub_type)
        img_bgr = cv2.cvtColor(np.array(base_img), cv2.COLOR_RGB2BGR)
        
        target_q = "HIGH" if u_idx % 2 == 0 else "MEDIUM"
        degraded_bgr, q_metrics = apply_quality_degradation(img_bgr, target_q)
        degraded_rgb = cv2.cvtColor(degraded_bgr, cv2.COLOR_BGR2RGB)
        final_img = Image.fromarray(degraded_rgb)
        
        filename = f"unknown_{u_idx}_{sub_type}.png"
        filepath = output_dir / "images" / "UNKNOWN" / filename
        final_img.save(filepath)
        
        metadata_list.append({
            "student_id": u_student_id,
            "doc_type": "UNKNOWN",
            "filepath": str(filepath.relative_to(output_dir)),
            "ground_truth": gt,
            "bounding_boxes": bboxes,
            "quality_metrics": q_metrics,
            "quality_label": q_metrics["quality_label"],
            "quality_score": q_metrics["quality_score"],
        })
            
    return metadata_list
