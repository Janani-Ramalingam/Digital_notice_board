// Digital Notice Board - Main JavaScript File

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    $('.alert').each(function() {
        var alert = $(this);
        setTimeout(function() {
            alert.fadeOut('slow');
        }, 5000);
    });

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });

    // Form validation enhancement
    $('form').on('submit', function() {
        var submitBtn = $(this).find('button[type="submit"]');
        var originalText = submitBtn.html();
        
        submitBtn.prop('disabled', true);
        submitBtn.html('<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing...');
        
        // Re-enable button after 10 seconds as fallback
        setTimeout(function() {
            submitBtn.prop('disabled', false);
            submitBtn.html(originalText);
        }, 10000);
    });

    // Search functionality with debounce
    var searchTimeout;
    $('.search-input').on('input', function() {
        clearTimeout(searchTimeout);
        var searchTerm = $(this).val();
        var form = $(this).closest('form');
        
        searchTimeout = setTimeout(function() {
            if (searchTerm.length >= 3 || searchTerm.length === 0) {
                form.submit();
            }
        }, 500);
    });

    // Confirmation dialogs for delete actions
    $('.delete-btn').on('click', function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        var itemName = $(this).data('item-name') || 'this item';
        
        if (confirm('Are you sure you want to delete ' + itemName + '? This action cannot be undone.')) {
            window.location.href = url;
        }
    });

    // Dynamic table row highlighting
    $('.table tbody tr').hover(
        function() {
            $(this).addClass('table-active');
        },
        function() {
            $(this).removeClass('table-active');
        }
    );

    // Copy to clipboard functionality
    $('.copy-btn').on('click', function() {
        var textToCopy = $(this).data('copy-text');
        navigator.clipboard.writeText(textToCopy).then(function() {
            showToast('Copied to clipboard!', 'success');
        });
    });

    // Print functionality
    $('.print-btn').on('click', function() {
        window.print();
    });

    // Export functionality
    $('.export-btn').on('click', function() {
        var format = $(this).data('format');
        var url = $(this).data('url');
        
        if (url) {
            window.open(url + '?format=' + format, '_blank');
        }
    });
});

// Notification System
class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.checkInterval = 30000; // Check every 30 seconds
        this.init();
    }

    init() {
        // Check for pending notifications on page load
        this.checkPendingNotifications();
        
        // Set up periodic checking
        setInterval(() => {
            this.checkPendingNotifications();
        }, this.checkInterval);
    }

    checkPendingNotifications() {
        // Only check for student users
        if (window.location.pathname.includes('/student/')) {
            $.ajax({
                url: '/student/api/notifications/',
                type: 'GET',
                success: (data) => {
                    this.handleNotifications(data.notifications);
                },
                error: (xhr, status, error) => {
                    console.log('Failed to fetch notifications:', error);
                }
            });
        }
    }

    handleNotifications(notifications) {
        notifications.forEach(notification => {
            if (!this.isNotificationShown(notification.id)) {
                this.showNotificationModal(notification);
                this.markNotificationAsShown(notification.id);
            }
        });
    }

    isNotificationShown(notificationId) {
        return this.notifications.includes(notificationId);
    }

    markNotificationAsShown(notificationId) {
        this.notifications.push(notificationId);
    }

    showNotificationModal(notification) {
        const modalId = 'notificationModal' + notification.id;
        
        // Check if modal already exists
        if ($('#' + modalId).length > 0) {
            $('#' + modalId).modal('show');
            return;
        }

        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-bell me-2"></i>
                                New Placement Drive - ${notification.company_name}
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <h6>${notification.title}</h6>
                                    <p class="text-muted">${notification.description}</p>
                                    
                                    <div class="row mt-3">
                                        <div class="col-6">
                                            <strong>Minimum CGPA:</strong> ${notification.min_cgpa}
                                        </div>
                                        <div class="col-6">
                                            <strong>Eligible Year:</strong> ${notification.eligible_year}
                                        </div>
                                    </div>
                                    
                                    <div class="mt-2">
                                        <strong>Eligible Departments:</strong>
                                        ${notification.eligible_departments.map(dept => 
                                            `<span class="badge bg-secondary me-1">${dept}</span>`
                                        ).join('')}
                                    </div>
                                    
                                    <div class="mt-2">
                                        <strong>Last Date:</strong> 
                                        <span class="text-danger">${new Date(notification.last_date).toLocaleString()}</span>
                                    </div>
                                </div>
                                <div class="col-md-4 text-center">
                                    <i class="bi bi-building text-primary" style="font-size: 4rem;"></i>
                                    <h5 class="mt-2">${notification.company_name}</h5>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <div class="w-100">
                                <p class="text-center mb-3">
                                    <strong>Please select your response:</strong>
                                </p>
                                <div class="row">
                                    <div class="col-6">
                                        <button type="button" class="btn btn-success w-100" onclick="submitResponse(${notification.id}, 'Opt-In')">
                                            <i class="bi bi-check-circle me-2"></i>Opt-In
                                        </button>
                                    </div>
                                    <div class="col-6">
                                        <button type="button" class="btn btn-danger w-100" onclick="submitResponse(${notification.id}, 'Opt-Out')">
                                            <i class="bi bi-x-circle me-2"></i>Opt-Out
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $('body').append(modalHtml);
        $('#' + modalId).modal('show');
    }
}

// Initialize notification system
const notificationSystem = new NotificationSystem();

// Global functions
function submitResponse(driveId, response) {
    // Validate driveId parameter
    if (!driveId || driveId === 'undefined' || driveId === 'null') {
        console.error('Invalid driveId:', driveId);
        alert('Error: Invalid drive ID. Please refresh the page and try again.');
        return;
    }
    
    const csrfToken = $('[name=csrfmiddlewaretoken]').val() || 
                     document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                     $('meta[name=csrf-token]').attr('content');
    
    $.ajax({
        url: `/student/submit-response/${driveId}/`,
        type: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
        },
        data: JSON.stringify({
            'drive_id': driveId,
            'response': response
        }),
        success: function(data) {
            if (data.success) {
                // Hide all modals for this drive
                $('.modal[id*="' + driveId + '"]').modal('hide');
                
                // Show success message
                showToast(data.message, 'success');
                
                // Reload page after a short delay to update statistics
                setTimeout(function() {
                    location.reload();
                }, 1500);
            } else {
                showToast(data.error || 'An error occurred', 'error');
            }
        },
        error: function(xhr, status, error) {
            showToast('Failed to submit response. Please try again.', 'error');
        }
    });
}

function showToast(message, type = 'info') {
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : 
                   type === 'error' ? 'bg-danger' : 
                   type === 'warning' ? 'bg-warning' : 'bg-info';
    
    const toastHtml = `
        <div class="toast align-items-center text-white ${bgClass} border-0" id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Create toast container if it doesn't exist
    if ($('#toast-container').length === 0) {
        $('body').append('<div id="toast-container" class="toast-container position-fixed top-0 end-0 p-3"></div>');
    }
    
    $('#toast-container').append(toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        $(this).remove();
    });
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

function toggleDriveStatus(driveId) {
    confirmAction('Are you sure you want to change the status of this drive?', function() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin-panel/drives/${driveId}/toggle-status/`;
        
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = $('[name=csrfmiddlewaretoken]').val() || 
                         document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        form.appendChild(csrfInput);
        document.body.appendChild(form);
        form.submit();
    });
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Loading overlay functions
function showLoading() {
    const loadingHtml = `
        <div id="loading-overlay" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style="background: rgba(0,0,0,0.5); z-index: 9999;">
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    if ($('#loading-overlay').length === 0) {
        $('body').append(loadingHtml);
    }
}

function hideLoading() {
    $('#loading-overlay').remove();
}

// Export global functions
window.submitResponse = submitResponse;
window.showToast = showToast;
window.confirmAction = confirmAction;
window.toggleDriveStatus = toggleDriveStatus;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
