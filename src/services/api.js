const INITIAL_APPLICATIONS = [];
const INITIAL_NOTIFICATIONS = [];

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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Service Layer (Integrated with FastAPI Backend)
 */
export const api = {
  // Real Backend Auth APIs
  async registerStudent(studentData) {
    const payload = {
      college_code: studentData.college_code?.trim(),
      full_name: studentData.full_name?.trim(),
      email: studentData.email?.trim().toLowerCase(),
      password: studentData.password,
      phone_number: studentData.phone_number?.trim() || null,
      government_id_number: studentData.government_id_number?.trim() || null,
      date_of_birth: studentData.date_of_birth || null,
      address: studentData.address?.trim() || null
    };

    const res = await fetch(`${API_BASE_URL}/auth/student/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Registration failed. Please check your details.';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return { success: true, student: data };
  },

  async registerAdmin(adminData) {
    const payload = {
      admin_setup_code: adminData.admin_setup_code?.trim(),
      full_name: adminData.full_name?.trim(),
      email: adminData.email?.trim().toLowerCase(),
      password: adminData.password,
      phone_number: adminData.phone_number?.trim() || null,
      department: adminData.department?.trim() || "Scholarship Cell",
      designation: adminData.designation?.trim() || "Verification Officer"
    };

    const res = await fetch(`${API_BASE_URL}/auth/admin/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const tokenData = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = tokenData.detail || 'Admin registration failed. Please check your setup code and details.';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    const profile = await this.getMe(tokenData.access_token);
    return {
      success: true,
      token: tokenData.access_token,
      user: profile
    };
  },

  async loginStudent(email, password, college_code = null) {
    const payload = {
      email: email.trim().toLowerCase(),
      password: password,
      role: 'STUDENT',
      ...(college_code ? { college_code: college_code.trim() } : {})
    };

    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const tokenData = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = tokenData.detail || 'Invalid email or password';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    // Fetch authenticated student profile from /auth/me
    const profile = await this.getMe(tokenData.access_token);

    return {
      success: true,
      token: tokenData.access_token,
      user: profile
    };
  },

  async loginAdmin(college_code, email, password) {
    const payload = {
      college_code: college_code.trim().toUpperCase(),
      email: email.trim().toLowerCase(),
      password: password
    };

    const res = await fetch(`${API_BASE_URL}/auth/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const tokenData = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = tokenData.detail || 'Invalid college code, email, or password';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    // Fetch authenticated user profile from /auth/me
    const profile = await this.getMe(tokenData.access_token);

    return {
      success: true,
      token: tokenData.access_token,
      user: profile
    };
  },

  async updateCollegeCode(college_code, accessToken) {
    const res = await fetch(`${API_BASE_URL}/admin/college-code`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ college_code: college_code.trim().toUpperCase() })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to update college code';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async getAdminCollege(accessToken) {
    const res = await fetch(`${API_BASE_URL}/admin/college`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to fetch admin college details';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async getMe(accessToken) {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (!res.ok) {
      throw new Error('Failed to fetch authenticated user profile');
    }
    return await res.json();
  },

  // Unified login helper
  async login(role, email, password, college_code = null) {
    if (role === 'ADMIN') {
      return this.loginAdmin(college_code || 'DEMO001', email, password);
    } else {
      return this.loginStudent(email, password, college_code);
    }
  },

  // Real Backend Application APIs
  async getScholarshipSchemes() {
    const res = await fetch(`${API_BASE_URL}/applications/schemes`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to fetch scholarship schemes');
    }
    return data.schemes || [];
  },

  async createApplication(scholarshipName, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ scholarship_name: scholarshipName })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to create application';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async getMyApplication(accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/my-application`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (res.status === 404) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to fetch application';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async getApplications(accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ([]));
    if (!res.ok) {
      const msg = data.detail || 'Failed to fetch college applications';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return Array.isArray(data) ? data : [];
  },

  async getApplicationById(id, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/${id}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to fetch application details';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async uploadDocument(applicationId, documentType, fileObj, accessToken) {
    const formData = new FormData();
    formData.append('document_type', documentType);
    if (fileObj) {
      formData.append('file', fileObj, fileObj.name);
    }

    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/documents`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      },
      body: formData
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to upload document';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  getDocumentFileUrl(applicationId, documentId) {
    return `${API_BASE_URL}/applications/${applicationId}/documents/${documentId}/file`;
  },

  async fetchDocumentBlob(applicationId, documentId, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/documents/${documentId}/file`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const msg = data.detail || 'Unable to open document. Please try again.';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    return await res.blob();
  },

  // Simulated AI Verification Engine
  async runAIVerification(applicationId) {
    await delay(1500); // Realistic AI processing simulation time
    const apps = getStoredApplications();
    const appIndex = apps.findIndex(a => a.id === applicationId);
    if (appIndex === -1) throw new Error("Application not found");

    const app = apps[appIndex];
    
    // Perform automated cross-document AI verification
    app.overallStatus = "VERIFIED";
    app.aiConfidence = 95;
    app.crossDocumentChecks = [
      { check: "Name Consistency Across Documents", status: "PASSED", details: `All documents match '${app.studentName}'` },
      { check: "Date of Birth Verification", status: "PASSED", details: "DOB verified against government records" },
      { check: "Income Eligibility Check", status: "PASSED", details: "Income criteria verified" },
      { check: "Domicile State Alignment", status: "PASSED", details: "State domicile criteria satisfied" }
    ];

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
