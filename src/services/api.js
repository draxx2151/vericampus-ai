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
      },
      cache: 'no-store'
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const msg = data.detail || 'Unable to open document. Please try again.';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    return await res.blob();
  },

  // Real Backend Verification Pipeline APIs
  async triggerVerification(applicationId, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/verify`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Automated document verification failed.');
      throw new Error(msg);
    }
    return data;
  },

  async getVerificationResult(applicationId, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/verification-result`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (res.status === 404) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to fetch verification result.');
      throw new Error(msg);
    }
    return data;
  },

  // Real Backend Physical Verification Appointment APIs
  async getMyPhysicalVerificationAppointment(accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/my-application/physical-verification`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (res.status === 404) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to retrieve physical verification appointment.');
      throw new Error(msg);
    }
    return data;
  },

  async getPhysicalVerificationAppointment(applicationId, accessToken) {
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/physical-verification`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (res.status === 404) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to retrieve appointment details.');
      throw new Error(msg);
    }
    return data;
  },

  // Real Backend Admin Review Action APIs
  async adminApproveApplication(applicationId, remarks, accessToken) {
    const payload = remarks ? { remarks: remarks.trim(), notes: remarks.trim() } : {};
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/admin-review/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to approve application.');
      throw new Error(msg);
    }
    return data;
  },

  async adminRequestCorrection(applicationId, { document_types, reason }, accessToken) {
    const payload = {
      document_types,
      reason: reason.trim()
    };
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/admin-review/request-correction`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to submit document correction request.');
      throw new Error(msg);
    }
    return data;
  },

  async adminSchedulePhysicalVerification(applicationId, { scheduled_date, scheduled_time, venue, purpose, instructions }, accessToken) {
    const payload = {
      scheduled_date,
      scheduled_time,
      venue: venue.trim(),
      instructions: instructions?.trim() || purpose?.trim() || 'Bring original certificates along with two photocopies.',
      purpose: purpose?.trim() || 'Verify original documents'
    };
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/admin-review/physical-verification`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to schedule physical verification appointment.');
      throw new Error(msg);
    }
    return data;
  },

  async adminCompletePhysicalVerification(applicationId, { result, remarks }, accessToken) {
    const payload = {
      result,
      remarks: remarks.trim()
    };
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/admin-review/physical-verification/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to record physical verification outcome.');
      throw new Error(msg);
    }
    return data;
  },

  async adminRejectApplication(applicationId, { reason, notes }, accessToken) {
    const payload = {
      reason: reason.trim(),
      notes: notes?.trim() || null
    };
    const res = await fetch(`${API_BASE_URL}/applications/${applicationId}/admin-review/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : (data.detail || 'Failed to reject application.');
      throw new Error(msg);
    }
    return data;
  },

  // Real Workflow Notifications APIs
  async getNotifications(accessToken) {
    const res = await fetch(`${API_BASE_URL}/notifications`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({ notifications: [], unread_count: 0, total_count: 0 }));
    if (!res.ok) {
      const msg = data.detail || 'Failed to fetch notifications';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async markNotificationAsRead(notificationId, accessToken) {
    const res = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to mark notification as read';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  async markAllNotificationsAsRead(accessToken) {
    const res = await fetch(`${API_BASE_URL}/notifications/mark-all-read`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || 'Failed to mark all notifications as read';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }
};
