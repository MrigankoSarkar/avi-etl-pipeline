const notifications = document.getElementById(

    "notifications"

);

const toastContainer = document.getElementById(

    "toastContainer"

);

/* =========================================
   TOAST POPUP
========================================= */

function showToast(

    message,

    type = "info"

){

    const toast = document.createElement(

        "div"

    );

    toast.className = `toast ${type}`;

    toast.innerText = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {

        toast.remove();

    }, 5000);
}

/* =========================================
   ACTIVITY NOTIFICATION
========================================= */

function showNotification(

    message,

    type = "info"

){

    const notification = document.createElement(

        "div"

    );

    notification.className = `notification ${type}`;

    notification.innerText = message;

    notifications.prepend(notification);

    setTimeout(() => {

        notification.remove();

    }, 7000);
}

/* =========================================
   PROGRESS SYSTEM
========================================= */

function updateProgress(

    progressBar,

    percentText,

    statusText,

    progress,

    message

){

    progressBar.style.width = `${progress}%`;

    percentText.innerText = `${progress}%`;

    statusText.innerText = message;
}

/* =========================================
   FILE SELECTION UI
========================================= */

const cleanInput = document.querySelector(

    '#cleanForm input[type="file"]'

);

const dbInput = document.querySelector(

    '#dbForm input[type="file"]'

);

const cleanFileInfo = document.getElementById(

    "cleanFileInfo"

);

const dbFileInfo = document.getElementById(

    "dbFileInfo"

);

const cleanFileName = document.getElementById(

    "cleanFileName"

);

const dbFileName = document.getElementById(

    "dbFileName"

);

cleanInput.addEventListener(

    "change",

    () => {

        const file = cleanInput.files[0];

        if(file){

            cleanFileInfo.classList.remove(

                "hidden"

            );

            cleanFileName.innerText = file.name;

            showToast(

                "Dataset selected successfully",

                "success"

            );
        }

    }

);

dbInput.addEventListener(

    "change",

    () => {

        const file = dbInput.files[0];

        if(file){

            dbFileInfo.classList.remove(

                "hidden"

            );

            dbFileName.innerText = file.name;

            showToast(

                "Cleaned CSV selected",

                "success"

            );
        }

    }

);

/* =========================================
   CLEAN DATASET
========================================= */

const cleanForm = document.getElementById(

    "cleanForm"

);

const cleanProgressBar = document.getElementById(

    "cleanProgressBar"

);

const cleanPercent = document.getElementById(

    "cleanPercent"

);

const cleanStatusText = document.getElementById(

    "cleanStatusText"

);

cleanForm.addEventListener(

    "submit",

    async (e) => {

        e.preventDefault();

        const button = cleanForm.querySelector(

            "button"

        );

        const formData = new FormData(cleanForm);

        button.disabled = true;

        button.innerText = "Cleaning Dataset...";

        updateProgress(

            cleanProgressBar,
            cleanPercent,
            cleanStatusText,

            10,

            "Uploading dataset..."

        );

        showToast(

            "Dataset upload started",

            "info"

        );

        showNotification(

            "Dataset cleaning initialized",

            "info"

        );

        try {

            const response = await fetch(

                "/upload",

                {

                    method:"POST",

                    body:formData

                }

            );

            updateProgress(

                cleanProgressBar,
                cleanPercent,
                cleanStatusText,

                50,

                "Cleaning records..."

            );

            if(!response.ok){

                throw new Error(

                    "Dataset cleaning failed"

                );
            }

            const blob = await response.blob();

            updateProgress(

                cleanProgressBar,
                cleanPercent,
                cleanStatusText,

                85,

                "Preparing download..."

            );

            const url = window.URL.createObjectURL(

                blob

            );

            const a = document.createElement(

                "a"

            );

            a.href = url;

            a.download = "cleaned_dataset.csv";

            document.body.appendChild(a);

            a.click();

            a.remove();

            updateProgress(

                cleanProgressBar,
                cleanPercent,
                cleanStatusText,

                100,

                "Dataset cleaned successfully"

            );

            showToast(

                "Dataset downloaded successfully",

                "success"

            );

            showNotification(

                "Cleaned dataset saved locally",

                "success"

            );

        } catch(error){

            updateProgress(

                cleanProgressBar,
                cleanPercent,
                cleanStatusText,

                0,

                "Cleaning failed"

            );

            showToast(

                error.message,

                "error"

            );

            showNotification(

                "Dataset cleaning failed",

                "error"

            );
        }

        button.disabled = false;

        button.innerText = "Clean & Download";

    }

);

/* =========================================
   NEON DB UPLOAD
========================================= */

const dbForm = document.getElementById(

    "dbForm"

);

const dbProgressBar = document.getElementById(

    "dbProgressBar"

);

const dbPercent = document.getElementById(

    "dbPercent"

);

const dbStatusText = document.getElementById(

    "dbStatusText"

);

dbForm.addEventListener(

    "submit",

    async (e) => {

        e.preventDefault();

        const button = dbForm.querySelector(

            "button"

        );

        const formData = new FormData(dbForm);

        button.disabled = true;

        button.innerText = "Uploading To NeonDB...";

        updateProgress(

            dbProgressBar,
            dbPercent,
            dbStatusText,

            10,

            "Uploading CSV..."

        );

        showToast(

            "NeonDB upload started",

            "info"

        );

        showNotification(

            "Database transaction initialized",

            "info"

        );

        try {

            const response = await fetch(

                "/upload-to-db",

                {

                    method:"POST",

                    body:formData

                }

            );

            updateProgress(

                dbProgressBar,
                dbPercent,
                dbStatusText,

                60,

                "Inserting rows..."

            );

            const data = await response.json();

            if(!response.ok){

                throw new Error(

                    data.error ||

                    "Database upload failed"

                );
            }

            updateProgress(

                dbProgressBar,
                dbPercent,
                dbStatusText,

                100,

                "Upload completed"

            );

            showToast(

                "NeonDB upload successful",

                "success"

            );

            showNotification(

                `Inserted ${data.rows_inserted} rows into NeonDB`,

                "success"

            );

        } catch(error){

            updateProgress(

                dbProgressBar,
                dbPercent,
                dbStatusText,

                0,

                "Upload failed"

            );

            showToast(

                error.message,

                "error"

            );

            showNotification(

                "Database upload failed",

                "error"

            );
        }

        button.disabled = false;

        button.innerText = "Upload To NeonDB";

    }

);