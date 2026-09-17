import { INITIAL_APPLICATIONS, INITIAL_NOTIFICATIONS, DEMO_USERS } from '../data/mockData';

// Storage keys
const APPS_STORAGE_KEY = 'vericampus_applications_v1';
const NOTIFS_STORAGE_KEY = 'vericampus_notifications_v1';

// Helper to initialize or read state
const getStoredApplications = () => {
  const data = localStorage.getItem(APPS_STORAGE_KEY);
  if (!data) {
    localStorage.setItem(APPS_STORAGE_KEY, JSON.stringify(INITIAL_APPLICATIONS));
    return INITIAL_APPLICATIONS;
  }
  return JSON.parse(data);
};

const saveStoredApplications = (apps) => {
  localStorage.setItem(APPS_STORAGE_KEY, JSON.stringify(apps));
};

const getStoredNotifications = () => {
  const data = localStorage.getItem(NOTIFS_STORAGE_KEY);
  if (!data) {
    localStorage.setItem(NOTIFS_STORAGE_KEY, JSON.stringify(INITIAL_NOTIFICATIONS));
    return INITIAL_NOTIFICATIONS;
  }
  return JSON.parse(data);
};

const saveStoredNotifications = (notifs) => {
  localStorage.setItem(NOTIFS_STORAGE_KEY, JSON.stringify(notifs));
};

// Simulated delay helper for realistic prototype feel
const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Service Layer (Prepared for Python + FastAPI backend integration)
 */
export const api = {
  // Auth API
  async login(role, email, password) {
    await delay(300);
    if (role === 'STUDENT') {
      const student = DEMO_USERS.students.find(s => s.email.toLowerCase() === email.toLowerCase()) || DEMO_USERS.students[0];
      return { success: true, user: student, token: "mock-jwt-token-student" };
    } else {
      return { success: true, user: DEMO_USERS.admin, token: "mock-jwt-token-admin" };
    }
  },

  // Application API
  async getApplications() {
    await delay(200);
    return getStoredApplications();
  },

  async getApplicationById(id) {
    await delay(200);
    const apps = getStoredApplications();
    return apps.find(a => a.id === id) || null;
  },

  async getApplicationByStudentId(studentId) {
    await delay(200);
    const apps = getStoredApplications();
    return apps.find(a => a.studentId === studentId) || apps[0];
  },

  // Document Upload API (Simulated)
  async uploadDocument(applicationId, documentType, fileObj) {
    await delay(400);
    const apps = getStoredApplications();
    const appIndex = apps.findIndex(a => a.id === applicationId);
    if (appIndex === -1) throw new Error("Application not found");

    const app = apps[appIndex];
    const fileName = fileObj ? fileObj.name : `demo_${documentType.toLowerCase()}.pdf`;
    
    // Key mapping
    const keyMap = {
      'Government ID': 'govId',
      '10th/12th Marksheet': 'marksheet',
      'Income Certificate': 'incomeCert',
      'Domicile Certificate': 'domicileCert'
    };
    
    const key = keyMap[documentType] || documentType;
    
    app.documents[key] = {
      id: `doc-${Date.now()}`,
      name: documentType,
      file: fileName,
      status: "UPLOADED",
      uploadTime: new Date().toLocaleString(),
      extractedData: {
        fullName: app.studentName,
        note: "OCR text pending verification"
      }
    };

    // Recount
    const uploadedCount = Object.values(app.documents).filter(Boolean).length;
    app.documentsUploadedCount = uploadedCount;
    if (uploadedCount === 4 && app.overallStatus === 'PROCESSING') {
      app.overallStatus = 'READY_FOR_AI';
    }

    saveStoredApplications(apps);
    return app;
  },

  // Simulated AI Verification Engine
  async runAIVerification(applicationId) {
    await delay(1500); // Realistic AI processing simulation time
    const apps = getStoredApplications();
    const appIndex = apps.findIndex(a => a.id === applicationId);
    if (appIndex === -1) throw new Error("Application not found");

    const app = apps[appIndex];
    
    // Check if this is Amit Patil vs Rahul Sharma vs others
    if (app.studentName.includes("Amit")) {
      app.overallStatus = "NEEDS_REVIEW";
      app.aiConfidence = 71; // Realistic prototype indicator
      app.meetingRequired = true;
      app.crossDocumentChecks = [
        { check: "Name Consistency Across Documents", status: "WARNING", details: "Name variation detected: 'Amit Patil' vs 'Amit Kumar Patil' vs 'Amit P. Patil'" },
        { check: "Date of Birth Verification", status: "PASSED", details: "DOB consistent across available records" },
        { check: "Income Eligibility Check", status: "PASSED", details: "Annual Income ₹1.8 Lakhs satisfies eligibility" },
        { check: "Domicile State Alignment", status: "PASSED", details: "State verified as Maharashtra" }
      ];
    } else {
      app.overallStatus = "VERIFIED";
      app.aiConfidence = 94; // Realistic prototype indicator
      app.crossDocumentChecks = [
        { check: "Name Consistency Across Documents", status: "PASSED", details: `All documents match '${app.studentName}'` },
        { check: "Date of Birth Verification", status: "PASSED", details: "DOB verified against Aadhaar & Marksheet" },
        { check: "Income Eligibility Check", status: "PASSED", details: "Income criteria verified" },
        { check: "Domicile State Alignment", status: "PASSED", details: "State domicile criteria satisfied" }
      ];
    }

    // Set document statuses
    Object.keys(app.documents).forEach(k => {
      if (app.documents[k]) {
        app.documents[k].status = (app.overallStatus === 'NEEDS_REVIEW' && (k === 'marksheet' || k === 'incomeCert')) ? 'FLAGGED' : 'VERIFIED';
      }
    });

    saveStoredApplications(apps);

    // Create Notification
    const notifs = getStoredNotifications();
    notifs.unshift({
      id: `notif-${Date.now()}`,
      recipientRole: "STUDENT",
      studentId: app.studentId,
      title: "AI Verification Complete",
      message: `AI verification completed for ${app.id}. Status: ${app.overallStatus === 'NEEDS_REVIEW' ? 'Needs Review' : 'Verified'}.`,
      timestamp: new Date().toLocaleString(),
      read: false,
      applicationId: app.id
    });

    if (app.overallStatus === 'NEEDS_REVIEW') {
      notifs.unshift({
        id: `notif-adm-${Date.now()}`,
        recipientRole: "ADMIN",
        title: "Application Flagged for Review",
        message: `Application ${app.id} (${app.studentName}) requires admin attention due to name inconsistency.`,
        timestamp: new Date().toLocaleString(),
        read: false,
        applicationId: app.id
      });
    }

    saveStoredNotifications(notifs);
    return app;
  },

  // Admin Review Decision
  async updateApplicationStatus(applicationId, newStatus, notes = "") {
    await delay(300);
    const apps = getStoredApplications();
    const appIndex = apps.findIndex(a => a.id === applicationId);
    if (appIndex === -1) throw new Error("Application not found");

    const app = apps[appIndex];
    app.overallStatus = newStatus;
    app.adminDecision = {
      status: newStatus,
      reviewedBy: "Admin Officer (Dr. V. K. Deshmukh)",
      reviewDate: new Date().toLocaleString(),
      notes: notes || `Admin manually updated status to ${newStatus}.`
    };

    saveStoredApplications(apps);
    return app;
  },

  // Admin Schedule Physical Verification Meeting
  async scheduleMeeting(applicationId, meetingData) {
    await delay(400);
    const apps = getStoredApplications();
    const appIndex = apps.findIndex(a => a.id === applicationId);
    if (appIndex === -1) throw new Error("Application not found");

    const app = apps[appIndex];
    app.meetingRequired = true;
    app.appointment = {
      date: meetingData.date,
      time: meetingData.time,
      venue: meetingData.venue || "Administrative Block, Room 204, Main Campus",
      purpose: meetingData.purpose || "Physical Document Verification & Signature Check",
      scheduledBy: "Admin Officer (Dr. V. K. Deshmukh)",
      status: "SCHEDULED"
    };

    saveStoredApplications(apps);

    // Notify Student
    const notifs = getStoredNotifications();
    notifs.unshift({
      id: `notif-meet-${Date.now()}`,
      recipientRole: "STUDENT",
      studentId: app.studentId,
      title: "Physical Document Verification Meeting Scheduled",
      message: `Admin scheduled your physical document verification meeting for ${meetingData.date} at ${meetingData.time}.`,
      timestamp: new Date().toLocaleString(),
      read: false,
      applicationId: app.id
    });
    saveStoredNotifications(notifs);

    return app;
  },

  // Notifications API
  async getNotifications(role, studentId = null) {
    await delay(200);
    const notifs = getStoredNotifications();
    if (role === 'ADMIN') {
      return notifs.filter(n => n.recipientRole === 'ADMIN');
    }
    return notifs.filter(n => n.recipientRole === 'STUDENT' && (!studentId || n.studentId === studentId));
  }
};
