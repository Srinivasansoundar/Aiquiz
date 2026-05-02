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
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [isQuizStarted, setIsQuizStarted] = useState(false);

  /**
   * Start a new quiz session
   */
  const startQuiz = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedAnswer(null);

    try {
      const data = await quizService.startQuiz();
      setQuizState(data);
      setIsQuizStarted(true);
    } catch (err) {
      setError(err.message || "Failed to start quiz");
    } finally {
      setLoading(false);
    }
  }, []);

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

  return {
    quizState,
    loading,
    error,
    selectedAnswer,
    setSelectedAnswer,
    isQuizStarted,
    startQuiz,
    submitAnswer,
  };
};
