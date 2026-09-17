export const INITIAL_APPLICATIONS = [
  {
    id: "VC-2026-001",
    studentId: "STU-1001",
    studentName: "Rahul Sharma",
    email: "rahul.sharma@example.edu",
    phone: "+91 98765 43210",
    scholarship: "Merit Scholarship 2026",
    appliedDate: "2026-09-10",
    overallStatus: "VERIFIED", // VERIFIED, NEEDS_REVIEW, PROCESSING, REJECTED
    aiConfidence: 94, // Percentage (Prototype-generated indicator)
    documentsUploadedCount: 4,
    totalDocumentsRequired: 4,
    meetingRequired: false,
    appointment: null,
    documents: {
      govId: {
        id: "doc-101",
        name: "Government ID / Aadhaar",
        file: "rahul_aadhaar_card.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-10 10:15 AM",
        extractedData: {
          fullName: "Rahul Sharma",
          idNumber: "XXXX-XXXX-4892",
          dob: "2004-05-14",
          address: "123 Academic Block, Pune, Maharashtra",
          gender: "Male"
        }
      },
      marksheet: {
        id: "doc-102",
        name: "10th/12th Marksheet",
        file: "rahul_hsc_marksheet.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-10 10:18 AM",
        extractedData: {
          fullName: "Rahul Sharma",
          rollNumber: "M-784910",
          passingYear: "2022",
          percentage: "91.4%",
          board: "Maharashtra State Board"
        }
      },
      incomeCert: {
        id: "doc-103",
        name: "Income Certificate",
        file: "rahul_income_2025.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-10 10:22 AM",
        extractedData: {
          fullName: "Rahul Sharma",
          fatherName: "Suresh Sharma",
          annualIncome: "₹ 2,40,000",
          certificateNo: "INC-2025-98341",
          issuingAuthority: "Tahsildar Office, Pune"
        }
      },
      domicileCert: {
        id: "doc-104",
        name: "Domicile Certificate",
        file: "rahul_domicile.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-10 10:25 AM",
        extractedData: {
          fullName: "Rahul Sharma",
          state: "Maharashtra",
          certificateNo: "DOM-MH-2024-551",
          issueDate: "2024-01-15"
        }
      }
    },
    crossDocumentChecks: [
      { check: "Name Consistency Across Documents", status: "PASSED", details: "All 4 documents match 'Rahul Sharma'" },
      { check: "Date of Birth Verification", status: "PASSED", details: "Aadhaar & Marksheet DOB match (14 May 2004)" },
      { check: "Income Eligibility Check", status: "PASSED", details: "Annual Income ₹2.4 Lakhs is below ₹5.0 Lakh threshold" },
      { check: "Domicile State Alignment", status: "PASSED", details: "State matches Maharashtra state scholarship quota" }
    ],
    adminDecision: {
      status: "APPROVED",
      reviewedBy: "Admin Officer (Dr. V. K. Deshmukh)",
      reviewDate: "2026-09-12 02:30 PM",
      notes: "All OCR extracted fields are verified and consistent. Merit criteria satisfied."
    }
  },
  {
    id: "VC-2026-002",
    studentId: "STU-1002",
    studentName: "Amit Patil",
    email: "amit.patil@example.edu",
    phone: "+91 98123 76543",
    scholarship: "Merit Scholarship 2026",
    appliedDate: "2026-09-14",
    overallStatus: "NEEDS_REVIEW",
    aiConfidence: 71,
    documentsUploadedCount: 4,
    totalDocumentsRequired: 4,
    meetingRequired: true,
    appointment: null, // Will be scheduled by Admin in main demo story
    documents: {
      govId: {
        id: "doc-201",
        name: "Government ID / Aadhaar",
        file: "amit_aadhaar.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-14 11:05 AM",
        extractedData: {
          fullName: "Amit Patil",
          idNumber: "XXXX-XXXX-9102",
          dob: "2003-11-20",
          address: "Plot 45, Green Park, Nashik, MH",
          gender: "Male"
        }
      },
      marksheet: {
        id: "doc-202",
        name: "10th/12th Marksheet",
        file: "amit_hsc_marksheet.jpg",
        status: "FLAGGED",
        uploadTime: "2026-09-14 11:10 AM",
        extractedData: {
          fullName: "Amit Kumar Patil",
          rollNumber: "N-401928",
          passingYear: "2022",
          percentage: "87.6%",
          board: "Maharashtra State Board"
        }
      },
      incomeCert: {
        id: "doc-203",
        name: "Income Certificate",
        file: "amit_income_cert.pdf",
        status: "FLAGGED",
        uploadTime: "2026-09-14 11:15 AM",
        extractedData: {
          fullName: "Amit P. Patil",
          fatherName: "Prakash Patil",
          annualIncome: "₹ 1,80,000",
          certificateNo: "INC-2025-11092",
          issuingAuthority: "Tahsildar Office, Nashik"
        }
      },
      domicileCert: {
        id: "doc-204",
        name: "Domicile Certificate",
        file: "amit_domicile_certificate.png",
        status: "VERIFIED",
        uploadTime: "2026-09-14 11:20 AM",
        extractedData: {
          fullName: "Amit Patil",
          state: "Maharashtra",
          certificateNo: "DOM-MH-2024-890",
          issueDate: "2024-03-10"
        }
      }
    },
    crossDocumentChecks: [
      { check: "Name Consistency Across Documents", status: "WARNING", details: "Name variation detected: 'Amit Patil' vs 'Amit Kumar Patil' vs 'Amit P. Patil'" },
      { check: "Date of Birth Verification", status: "PASSED", details: "DOB consistent across available records" },
      { check: "Income Eligibility Check", status: "PASSED", details: "Annual Income ₹1.8 Lakhs satisfies eligibility" },
      { check: "Domicile State Alignment", status: "PASSED", details: "State verified as Maharashtra" }
    ],
    adminDecision: null
  },
  {
    id: "VC-2026-003",
    studentId: "STU-1003",
    studentName: "Priya Shah",
    email: "priya.shah@example.edu",
    phone: "+91 97654 12389",
    scholarship: "National Need-Based Scholarship 2026",
    appliedDate: "2026-09-16",
    overallStatus: "PROCESSING",
    aiConfidence: 45,
    documentsUploadedCount: 3,
    totalDocumentsRequired: 4,
    meetingRequired: false,
    appointment: null,
    documents: {
      govId: {
        id: "doc-301",
        name: "Government ID / Aadhaar",
        file: "priya_aadhaar.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-16 09:30 AM",
        extractedData: {
          fullName: "Priya Shah",
          idNumber: "XXXX-XXXX-6712",
          dob: "2004-02-08",
          address: "A-12 University Hostel, Mumbai",
          gender: "Female"
        }
      },
      marksheet: {
        id: "doc-302",
        name: "10th/12th Marksheet",
        file: "priya_marksheet.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-16 09:35 AM",
        extractedData: {
          fullName: "Priya Shah",
          rollNumber: "M-112094",
          passingYear: "2022",
          percentage: "94.2%",
          board: "CBSE Board"
        }
      },
      incomeCert: {
        id: "doc-303",
        name: "Income Certificate",
        file: "priya_income.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-16 09:40 AM",
        extractedData: {
          fullName: "Priya Shah",
          fatherName: "Ramesh Shah",
          annualIncome: "₹ 3,10,000",
          certificateNo: "INC-2025-44912",
          issuingAuthority: "Tahsildar Office, Mumbai"
        }
      },
      domicileCert: null
    },
    crossDocumentChecks: [
      { check: "Document Completeness", status: "PENDING", details: "Domicile Certificate has not been uploaded yet" },
      { check: "Name Consistency Across Documents", status: "PASSED", details: "Uploaded 3 documents match 'Priya Shah'" }
    ],
    adminDecision: null
  },
  {
    id: "VC-2026-004",
    studentId: "STU-1004",
    studentName: "Sneha Kulkarni",
    email: "sneha.kulkarni@example.edu",
    phone: "+91 99887 76655",
    scholarship: "Excellence in Tech Scholarship 2026",
    appliedDate: "2026-09-11",
    overallStatus: "VERIFIED",
    aiConfidence: 92,
    documentsUploadedCount: 4,
    totalDocumentsRequired: 4,
    meetingRequired: true,
    appointment: {
      date: "2026-09-25",
      time: "11:30 AM",
      venue: "Administrative Block, Room 204, VeriCampus Main Campus",
      purpose: "Physical Document Verification & Original Signature Check",
      scheduledBy: "Admin Officer (Prof. S. R. Joshi)",
      status: "SCHEDULED"
    },
    documents: {
      govId: {
        id: "doc-401",
        name: "Government ID / Aadhaar",
        file: "sneha_aadhaar.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-11 03:10 PM",
        extractedData: {
          fullName: "Sneha Kulkarni",
          idNumber: "XXXX-XXXX-3341",
          dob: "2003-08-30",
          address: "Shivaji Nagar, Nagpur, MH",
          gender: "Female"
        }
      },
      marksheet: {
        id: "doc-402",
        name: "10th/12th Marksheet",
        file: "sneha_marksheet.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-11 03:15 PM",
        extractedData: {
          fullName: "Sneha Kulkarni",
          rollNumber: "N-902145",
          passingYear: "2021",
          percentage: "95.8%",
          board: "Maharashtra State Board"
        }
      },
      incomeCert: {
        id: "doc-403",
        name: "Income Certificate",
        file: "sneha_income.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-11 03:20 PM",
        extractedData: {
          fullName: "Sneha Kulkarni",
          fatherName: "Anand Kulkarni",
          annualIncome: "₹ 1,50,000",
          certificateNo: "INC-2025-77102",
          issuingAuthority: "Tahsildar Office, Nagpur"
        }
      },
      domicileCert: {
        id: "doc-404",
        name: "Domicile Certificate",
        file: "sneha_domicile.pdf",
        status: "VERIFIED",
        uploadTime: "2026-09-11 03:25 PM",
        extractedData: {
          fullName: "Sneha Kulkarni",
          state: "Maharashtra",
          certificateNo: "DOM-MH-2024-331",
          issueDate: "2024-02-18"
        }
      }
    },
    crossDocumentChecks: [
      { check: "Name Consistency Across Documents", status: "PASSED", details: "All documents match 'Sneha Kulkarni'" },
      { check: "Date of Birth Verification", status: "PASSED", details: "DOB consistent across records" },
      { check: "Income Eligibility Check", status: "PASSED", details: "Income ₹1.5 Lakhs satisfies merit criteria" }
    ],
    adminDecision: {
      status: "APPROVED_WITH_PHYSICAL_VERIFICATION",
      reviewedBy: "Admin Officer (Prof. S. R. Joshi)",
      reviewDate: "2026-09-13 11:00 AM",
      notes: "AI verification passed. Physical verification scheduled to inspect original certificates as required by scholarship committee guidelines."
    }
  }
];

export const INITIAL_NOTIFICATIONS = [
  {
    id: "notif-1",
    recipientRole: "ADMIN",
    title: "Needs Review Alert",
    message: "Application VC-2026-002 (Amit Patil) requires review due to OCR name variation.",
    timestamp: "2026-09-14 11:21 AM",
    read: false,
    applicationId: "VC-2026-002"
  },
  {
    id: "notif-2",
    recipientRole: "STUDENT",
    studentId: "STU-1004",
    title: "Physical Verification Appointment Scheduled",
    message: "Admin scheduled physical verification for 25 Sept 2026 at 11:30 AM at Room 204.",
    timestamp: "2026-09-13 11:05 AM",
    read: false,
    applicationId: "VC-2026-004"
  },
  {
    id: "notif-3",
    recipientRole: "STUDENT",
    studentId: "STU-1001",
    title: "AI Verification Completed",
    message: "Your application VC-2026-001 has passed AI document verification.",
    timestamp: "2026-09-10 10:30 AM",
    read: true,
    applicationId: "VC-2026-001"
  }
];

export const DEMO_USERS = {
  students: [
    {
      id: "STU-1002",
      name: "Amit Patil",
      email: "amit.patil@example.edu",
      applicationId: "VC-2026-002",
      role: "STUDENT"
    },
    {
      id: "STU-1001",
      name: "Rahul Sharma",
      email: "rahul.sharma@example.edu",
      applicationId: "VC-2026-001",
      role: "STUDENT"
    },
    {
      id: "STU-1004",
      name: "Sneha Kulkarni",
      email: "sneha.kulkarni@example.edu",
      applicationId: "VC-2026-004",
      role: "STUDENT"
    },
    {
      id: "STU-1003",
      name: "Priya Shah",
      email: "priya.shah@example.edu",
      applicationId: "VC-2026-003",
      role: "STUDENT"
    }
  ],
  admin: {
    id: "ADM-9001",
    name: "Dr. V. K. Deshmukh",
    email: "admin@vericampus.edu",
    role: "ADMIN",
    department: "Scholarship Cell & Verification Authority"
  }
};
