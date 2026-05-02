/**
 * Quiz Component - Main quiz interface with beautiful UI
 */

import React from "react";
import { useQuiz } from "../hooks/useQuiz";

export const QuizComponent = () => {
  const {
    quizState,
    loading,
    error,
    selectedAnswer,
    setSelectedAnswer,
    isQuizStarted,
    startQuiz,
    submitAnswer,
  } = useQuiz();

  const handleAnswerSelect = (option) => {
    setSelectedAnswer(option);
  };

  const handleSubmitAnswer = () => {
    if (selectedAnswer) {
      submitAnswer(selectedAnswer);
    }
  };

  const handleGenerateQuiz = () => {
    startQuiz();
  };

  const handleRetry = () => {
    startQuiz();
  };

  // Show loading state
  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="flex flex-col items-center gap-5">
          <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
          <p className="text-white text-lg font-medium">Loading question...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !isQuizStarted) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-12 text-center">
          <div className="text-6xl mb-6">⚠️</div>
          <p className="text-gray-700 mb-8">{error}</p>
          <button 
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold py-3 rounded-lg hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
            onClick={handleRetry}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Show initial state - Generate button
  if (!isQuizStarted) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-16 text-center animate-in fade-in duration-500">
          <div className="text-8xl mb-6">🎯</div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Welcome to AI Quiz</h1>
          <p className="text-gray-600 text-lg mb-8">Test your knowledge with our AI-powered quiz system</p>
          <button 
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold py-4 px-8 rounded-lg text-lg hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
            onClick={handleGenerateQuiz}
          >
            🚀 Generate Quiz
          </button>
        </div>
      </div>
    );
  }

  // Show quiz completion state
  if (quizState.status === "completed") {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-16 text-center animate-in fade-in duration-500">
          <div className="text-8xl mb-6">🎉</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Quiz Completed!</h1>
          <p className="text-gray-600 text-base mb-8">
            Great job! You've finished all the questions.
          </p>
          <button 
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold py-3 rounded-lg hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
            onClick={handleRetry}
          >
            Start New Quiz
          </button>
        </div>
      </div>
    );
  }

  // Show quiz question
  return (
    <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in fade-in duration-500">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-6 flex justify-between items-center">
          <div className="bg-white bg-opacity-20 text-white text-xs font-bold uppercase tracking-wider py-2 px-4 rounded-full">
            Quiz
          </div>
          <button 
            className="text-white text-2xl hover:scale-125 transition-transform"
            onClick={handleRetry}
            title="Exit Quiz"
          >
            ✕
          </button>
        </div>

        {/* Question Section */}
        <div className="p-10">
          <h2 className="text-3xl font-bold text-gray-900 leading-relaxed">
            {quizState.question}
          </h2>
        </div>

        {/* Options Section */}
        <div className="px-10 pb-6">
          <div className="text-sm font-bold text-gray-600 uppercase tracking-wider mb-4">
            Select your answer:
          </div>
          <div className="space-y-3">
            {quizState.options && quizState.options.length > 0 ? (
              quizState.options.map((option, index) => (
                <button
                  key={index}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all duration-300 transform hover:translate-x-1 ${
                    selectedAnswer === option
                      ? "bg-blue-500 text-white shadow-lg"
                      : "bg-gray-100 text-gray-800 hover:bg-gray-200 border-2 border-gray-100"
                  }`}
                  onClick={() => handleAnswerSelect(option)}
                >
                  <span className={`flex justify-center items-center w-8 h-8 rounded-lg font-bold text-sm flex-shrink-0 ${
                    selectedAnswer === option
                      ? "bg-white bg-opacity-30 text-white"
                      : "bg-gray-200 text-gray-800"
                  }`}>
                    {String.fromCharCode(65 + index)}
                  </span>
                  <span className="text-left font-medium">
                    {option}
                  </span>
                </button>
              ))
            ) : (
              <p className="text-center text-gray-400 py-5">No options available</p>
            )}
          </div>
        </div>

        {/* Hint Section - Only shown if hint is available */}
        {quizState.hint && (
          <div className="mx-10 mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-lg animate-in fade-in duration-300">
            <div className="flex items-center gap-2 mb-2 font-bold text-yellow-800">
              <span className="text-lg">💡</span>
              <span className="text-xs uppercase tracking-wider">Hint</span>
              {quizState.hint_attempt > 0 && (
                <span className="ml-auto text-xs font-semibold text-yellow-700">
                  Used: {quizState.hint_attempt}
                </span>
              )}
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">
              {quizState.hint}
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mx-10 mb-6 flex items-center gap-3 p-4 bg-red-50 border-l-4 border-red-400 rounded-lg">
            <span className="text-xl">⚠️</span>
            <span className="text-sm text-red-700 font-medium">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <div className="px-10 pb-10 border-t border-gray-200">
          <button
            className={`w-full mt-6 font-bold py-4 px-6 rounded-lg text-white text-lg transition-all duration-300 transform hover:-translate-y-1 ${
              !selectedAnswer || loading
                ? "bg-gray-400 cursor-not-allowed opacity-60"
                : "bg-gradient-to-r from-blue-500 to-purple-600 hover:shadow-lg"
            }`}
            onClick={handleSubmitAnswer}
            disabled={!selectedAnswer || loading}
          >
            {loading ? "Submitting..." : "Submit Answer"}
          </button>
        </div>
      </div>
    </div>
  );
};
