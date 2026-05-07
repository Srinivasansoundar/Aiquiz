/**
 * useQuiz Hook - Manages quiz state and logic
 */

import { useState, useCallback } from "react";
import { quizService } from "../services/quizService";

export const useQuiz = () => {
  const [quizState, setQuizState] = useState({
    question: null,
    options: [],
    hint: null,
    hint_attempt: 0,
    status: null,
    difficulty: null,
    topic: null,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [isQuizStarted, setIsQuizStarted] = useState(false);
  const [collectionName, setCollectionName] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [topicInput, setTopicInput] = useState("");
  const [quizReport, setQuizReport] = useState(null);

  /**
   * Upload and ingest a PDF file
   */
  const uploadPDF = useCallback(async (file) => {
    setUploadLoading(true);
    setError(null);
    setUploadStatus("Uploading and processing PDF...");

    try {
      const response = await quizService.uploadPDF(file);

      if (response.success) {
        setCollectionName(response.collection_name);
        setUploadStatus(
          `✅ PDF processed successfully! (${response.total_chunks} chunks)`
        );
      } else {
        throw new Error(response.error || "Failed to upload PDF");
      }
    } catch (err) {
      setError(err.message || "Failed to upload PDF");
      setUploadStatus(null);
    } finally {
      setUploadLoading(false);
    }
  }, []);

  /**
   * Start a new quiz session with collection name (without topic)
   */
  const startQuiz = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedAnswer(null);

    try {
      const data = await quizService.startQuiz(collectionName);
      setQuizState(data);
      setIsQuizStarted(true);
    } catch (err) {
      setError(err.message || "Failed to start quiz");
    } finally {
      setLoading(false);
    }
  }, [collectionName]);

  /**
   * Start a new quiz session with topic
   */
  const startQuizWithTopic = useCallback(async (topic) => {
    if (!topic.trim()) {
      setError("Please enter a topic");
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedAnswer(null);

    try {
      const data = await quizService.startQuiz(collectionName, topic, 5);
      setQuizState(data);
      setIsQuizStarted(true);
      setTopicInput("");
    } catch (err) {
      setError(err.message || "Failed to start quiz with topic");
    } finally {
      setLoading(false);
    }
  }, [collectionName]);

  /**
   * Submit an answer and get the next question
   */
  const submitAnswer = useCallback(async (answer) => {
    setLoading(true);
    setError(null);
    setSelectedAnswer(null);

    try {
      const data = await quizService.submitAnswer(answer);
      setQuizState(data);
    } catch (err) {
      setError(err.message || "Failed to submit answer");
    } finally {
      setLoading(false);
    }
  }, []);

  const resetUpload = useCallback(() => {
    setCollectionName(null);
    setUploadStatus(null);
    setIsQuizStarted(false);
    setQuizState({
      question: null,
      options: [],
      hint: null,
      hint_attempt: 0,
      status: null,
      difficulty: null,
    });
  }, []);

  /**
   * Go back to topic selection without clearing the uploaded PDF
   */
  const goBackToTopicSelection = useCallback(() => {
    setIsQuizStarted(false);
    setQuizState({
      question: null,
      options: [],
      hint: null,
      hint_attempt: 0,
      status: null,
      difficulty: null,
    });
    setSelectedAnswer(null);
    setError(null);
  }, []);

  /**
   * Delete the collection and go back to upload PDF page
   */
  const deleteCollectionAndReset = useCallback(async () => {
    try {
      if (collectionName) {
        await quizService.deleteCollection(collectionName);
      }
      // Reset all state
      resetUpload();
    } catch (err) {
      console.error("Error deleting collection:", err);
      // Still reset even if deletion fails
      resetUpload();
    }
  }, [collectionName]);

  /**
   * Fetch the quiz report after quiz completion
   */
  const fetchQuizReport = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await quizService.getReport();
      
      if (response.success) {
        setQuizReport(response.report);
      } else {
        throw new Error(response.error || "Failed to fetch report");
      }
    } catch (err) {
      setError(err.message || "Failed to fetch report");
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Reset and start a new quiz
   */
  const startNewQuiz = useCallback(() => {
    setQuizReport(null);
    setIsQuizStarted(false);
    setQuizState({
      question: null,
      options: [],
      hint: null,
      hint_attempt: 0,
      status: null,
      difficulty: null,
    });
    setSelectedAnswer(null);
    setError(null);
  }, []);

  return {
    quizState,
    loading,
    error,
    selectedAnswer,
    setSelectedAnswer,
    isQuizStarted,
    collectionName,
    uploadStatus,
    uploadLoading,
    topicInput,
    setTopicInput,
    quizReport,
    uploadPDF,
    startQuiz,
    startQuizWithTopic,
    submitAnswer,
    resetUpload,
    goBackToTopicSelection,
    deleteCollectionAndReset,
    fetchQuizReport,
    startNewQuiz,
  };
};
