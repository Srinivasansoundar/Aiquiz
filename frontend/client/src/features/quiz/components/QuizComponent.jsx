/**
 * Quiz Component - Main quiz interface with beautiful UI
 */

import React, { useRef, useEffect } from "react";
import { useQuiz } from "../hooks/useQuiz";
import { QuizReportComponent } from "./QuizReportComponent";

export const QuizComponent = () => {
  const {
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
  } = useQuiz();

  // Fetch report when quiz is completed
  useEffect(() => {
    if (quizState.status === "completed" && !quizReport) {
      fetchQuizReport();
    }
  }, [quizState.status, quizReport, fetchQuizReport]);

  const fileInputRef = useRef(null);

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
    resetUpload();
  };

  const handleFileSelect = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await uploadPDF(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Get difficulty badge styling
  const getDifficultyStyles = (difficulty) => {
    const baseClasses = "text-white text-xs font-bold uppercase tracking-wider py-2 px-4 rounded-full";
    switch (difficulty?.toLowerCase()) {
      case "easy":
        return `${baseClasses} bg-green-500 bg-opacity-90`;
      case "medium":
        return `${baseClasses} bg-yellow-500 bg-opacity-90`;
      case "hard":
        return `${baseClasses} bg-red-500 bg-opacity-90`;
      default:
        return `${baseClasses} bg-blue-600 bg-opacity-90`;
    }
  };

  // Get difficulty emoji
  const getDifficultyEmoji = (difficulty) => {
    switch (difficulty?.toLowerCase()) {
      case "easy":
        return "🟢";
      case "medium":
        return "🟡";
      case "hard":
        return "🔴";
      default:
        return "❓";
    }
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

  // Show initial state - Upload PDF
  if (!isQuizStarted && !collectionName) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-16 text-center animate-in fade-in duration-500">
          <div className="text-8xl mb-6">📄</div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">AI Quiz Generator</h1>
          <p className="text-gray-600 text-lg mb-8">Upload a PDF to generate an AI-powered quiz</p>
          
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          {/* Upload button */}
          <button 
            className={`w-full font-bold py-4 px-8 rounded-lg text-lg transition-all duration-300 transform hover:-translate-y-1 ${
              uploadLoading
                ? "bg-gray-400 text-white cursor-not-allowed"
                : "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-lg"
            }`}
            onClick={handleUploadClick}
            disabled={uploadLoading}
          >
            {uploadLoading ? "Processing..." : "📤 Upload PDF"}
          </button>

          {/* Upload status message */}
          {uploadStatus && (
            <div className="mt-4 p-4 bg-green-50 border-l-4 border-green-400 rounded-lg animate-in fade-in duration-300">
              <p className="text-green-700 text-sm font-medium">{uploadStatus}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Show state after PDF uploaded - Generate Quiz or Quiz with Topic
  if (!isQuizStarted && collectionName && !uploadLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        {/* Close button - top right */}
        <button 
          className="fixed top-6 right-6 text-white text-3xl hover:scale-125 transition-transform z-50"
          onClick={deleteCollectionAndReset}
          title="Close and delete collection"
        >
          ✕
        </button>

        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-12 text-center animate-in fade-in duration-500">
          <div className="text-8xl mb-6">🎯</div>
          <h1 className="text-4xl font-bold text-gray-900 mb-8">Ready to Quiz!</h1>

          {/* Error message if topic submission fails */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded-lg">
              <p className="text-red-700 text-sm font-medium">{error}</p>
            </div>
          )}

          {/* Topic Form */}
          <div className="mb-8">
            <label className="block text-gray-700 text-sm font-bold mb-3 text-left">
              🔍 Search by Topic (Optional)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    startQuizWithTopic(topicInput);
                  }
                }}
                placeholder="e.g., CPU Scheduling, Memory Management..."
                className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
              />
              <button
                onClick={() => startQuizWithTopic(topicInput)}
                disabled={loading || !topicInput.trim()}
                className={`px-6 py-3 rounded-lg font-semibold text-white transition-all duration-300 transform hover:-translate-y-1 ${
                  loading || !topicInput.trim()
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-blue-500 to-purple-600 hover:shadow-lg"
                }`}
              >
                {loading ? "Loading..." : "Go"}
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="relative mb-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500 font-medium">or</span>
            </div>
          </div>

          {/* Generate Quiz Button */}
          <p className="text-gray-600 text-sm mb-4">Generate quiz from all content</p>
          <button
            className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-4 px-8 rounded-lg text-lg hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1 mb-3"
            onClick={handleGenerateQuiz}
            disabled={loading}
          >
            {loading ? "Loading..." : "🚀 Generate Quiz"}
          </button>
        </div>
      </div>
    );
  }

  // Show quiz report if available
  if (quizReport) {
    return <QuizReportComponent report={quizReport} onNewQuiz={startNewQuiz} />;
  }

  // Show quiz completion state (loading report)
  if (quizState.status === "completed") {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-16 text-center animate-in fade-in duration-500">
          <div className="text-6xl mb-6">⏳</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Loading Your Report...</h1>
          <p className="text-gray-600 text-base mb-8">
            Generating your comprehensive quiz report...
          </p>
          <div className="flex justify-center">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
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
          <div className="flex gap-3 items-center flex-wrap">
            <div className="bg-white bg-opacity-20 text-black text-xs font-bold uppercase tracking-wider py-2 px-4 rounded-full">
              Quiz
            </div>
            {quizState.topic && (
              <div className="bg-white bg-opacity-20 text-black text-xs font-bold uppercase tracking-wider py-2 px-4 rounded-full">
                📚 {quizState.topic}
              </div>
            )}
            <div className={getDifficultyStyles(quizState.difficulty)}>
              {getDifficultyEmoji(quizState.difficulty)} {quizState.difficulty || "Loading"}
            </div>
          </div>
          <button 
            className="text-white text-2xl hover:scale-125 transition-transform"
            onClick={goBackToTopicSelection}
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
