/**
 * Quiz Service - Handles all API calls to the quiz backend
 */

const API_BASE_URL = "http://localhost:8000/quiz";

export const quizService = {
  /**
   * Start a new quiz session
   * @returns {Promise<{question, options, hint, hint_attempt, status}>}
   */
  startQuiz: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/start`, {
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
