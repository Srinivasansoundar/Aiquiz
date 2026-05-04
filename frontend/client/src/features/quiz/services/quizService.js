/**
 * Quiz Service - Handles all API calls to the quiz backend
 */

const API_BASE_URL = "http://localhost:8000/quiz";

// quizservice is an object
export const quizService = {
  /**
   * Upload a PDF file for ingestion
   * @param {File} file - The PDF file to upload
   * @returns {Promise<{success, collection_name, total_chunks, message}>}
   */
  uploadPDF: async (file) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Failed to upload PDF: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error uploading PDF:", error);
      throw error;
    }
  },

  /**
   * Start a new quiz session
   * @param {string} collectionName - The collection name from PDF ingestion
   * @returns {Promise<{question, options, hint, hint_attempt, status}>}
   */
  startQuiz: async (collectionName = null) => {
    try {
      const url = new URL(`${API_BASE_URL}/start`);
      if (collectionName) {
        url.searchParams.append("collection_name", collectionName);
      }

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to start quiz: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error starting quiz:", error);
      throw error;
    }
  },

  /**
   * Submit an answer and get the next question
   * @param {string} answer - The user's answer
   * @returns {Promise<{question, options, hint, hint_attempt, status}>}
   */
  submitAnswer: async (answer) => {
    try {
      const response = await fetch(`${API_BASE_URL}/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ answer }),
      });

      if (!response.ok) {
        throw new Error(`Failed to submit answer: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error submitting answer:", error);
      throw error;
    }
  },
};
