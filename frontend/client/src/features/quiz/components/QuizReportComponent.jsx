/**
 * Quiz Report Component - Beautiful display of quiz results
 */

import React from "react";
import "./QuizReportComponent.css";

export const QuizReportComponent = ({ report, onNewQuiz }) => {
  if (!report) {
    return <div className="report-loading">Loading report...</div>;
  }

  const {
    total_questions,
    correct_answers,
    wrong_answers,
    score_percentage,
    is_topic_based,
    selected_topic,
    strong_topics,
    weak_topics,
    questions,
  } = report;

  // Determine score status
  const getScoreStatus = (percentage) => {
    if (percentage >= 80) return { label: "Excellent!", emoji: "🎉", color: "excellent" };
    if (percentage >= 60) return { label: "Good Job!", emoji: "👍", color: "good" };
    if (percentage >= 40) return { label: "Keep Trying!", emoji: "💪", color: "fair" };
    return { label: "Try Again!", emoji: "📚", color: "poor" };
  };

  const scoreStatus = getScoreStatus(score_percentage);

  const getQuestionStatus = (question) => {
    if (question.is_correct) {
      return { icon: "✅", class: "correct" };
    }
    if (question.wrong_on_first_try) {
      return { icon: "❌", class: "wrong-first-try" };
    }
    return { icon: "⚠️", class: "wrong" };
  };

  return (
    <div className="quiz-report-container">
      {/* Header */}
      <div className="report-header">
        <div className="report-title-section">
          <h1 className="report-main-title">Quiz Completed! 🎓</h1>
          <p className="report-subtitle">Here's your comprehensive performance report</p>
        </div>
      </div>

      {/* Score Summary Card */}
      <div className={`score-summary-card ${scoreStatus.color}`}>
        <div className="score-emoji">{scoreStatus.emoji}</div>
        <div className="score-status">{scoreStatus.label}</div>
        <div className="score-percentage">{Math.round(score_percentage)}%</div>
        <div className="score-details">
          <div className="score-item">
            <span className="score-label">Correct</span>
            <span className="score-value correct-color">{correct_answers}/{total_questions}</span>
          </div>
          <div className="score-divider">|</div>
          <div className="score-item">
            <span className="score-label">Wrong</span>
            <span className="score-value wrong-color">{wrong_answers}/{total_questions}</span>
          </div>
        </div>
      </div>

      {/* Topic Analysis - Only for general quizzes */}
      {!is_topic_based && (
        <div className="topic-analysis-section">
          <h2 className="section-title">📊 Topic Analysis</h2>
          
          {/* Strong Topics */}
          {strong_topics && strong_topics.length > 0 && (
            <div className="topic-subsection">
              <h3 className="subsection-title strong">💪 Strong Topics</h3>
              <div className="topics-grid">
                {strong_topics.map((topic, idx) => (
                  <div key={idx} className="topic-card strong-topic">
                    <div className="topic-name">{topic.topic}</div>
                    <div className="topic-score-large">{topic.score_percentage}%</div>
                    <div className="topic-stats">
                      <span className="stat">{topic.correct_answers}/{topic.total_questions}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weak Topics */}
          {weak_topics && weak_topics.length > 0 && (
            <div className="topic-subsection">
              <h3 className="subsection-title weak">📉 Weak Topics - Focus Here!</h3>
              <div className="topics-grid">
                {weak_topics.map((topic, idx) => (
                  <div key={idx} className="topic-card weak-topic">
                    <div className="topic-name">{topic.topic}</div>
                    <div className="topic-score-large">{topic.score_percentage}%</div>
                    <div className="topic-stats">
                      <span className="stat">{topic.correct_answers}/{topic.total_questions}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Topic-Based Quiz Info */}
      {is_topic_based && selected_topic && (
        <div className="topic-based-info">
          <div className="topic-badge">
            <span className="topic-label">📚 Topic:</span>
            <span className="topic-value">{selected_topic}</span>
          </div>
        </div>
      )}

      {/* Questions Review */}
      <div className="questions-review-section">
        <h2 className="section-title">📋 Questions Review</h2>
        <div className="questions-list">
          {questions.map((question, idx) => {
            const status = getQuestionStatus(question);
            return (
              <div key={idx} className={`question-review-card ${status.class}`}>
                <div className="question-header">
                  <div className="question-number-status">
                    <span className="question-number">Q{question.question_num}</span>
                    <span className={`question-status ${status.class}`}>{status.icon}</span>
                  </div>
                  <div className="question-difficulty-topic">
                    <span className={`difficulty-badge ${question.difficulty}`}>
                      {question.difficulty.toUpperCase()}
                    </span>
                    <span className="question-topic">{question.topic}</span>
                  </div>
                </div>

                <div className="question-text">{question.question}</div>

                <div className="options-display">
                  {question.options.map((option, optIdx) => {
                    const isCorrectOption = option === question.correct_answer;
                    const isUserAnswer = option === question.user_answer;
                    
                    let optionClass = "option-item";
                    if (isCorrectOption) optionClass += " correct-option";
                    if (isUserAnswer && !isCorrectOption) optionClass += " wrong-option";
                    if (isUserAnswer && isCorrectOption) optionClass += " correct-answer-selected";

                    return (
                      <div key={optIdx} className={optionClass}>
                        <div className="option-content">
                          <span className="option-letter">
                            {String.fromCharCode(65 + optIdx)}.
                          </span>
                          <span className="option-text">{option}</span>
                        </div>
                        {isCorrectOption && <span className="option-indicator">✓ Correct</span>}
                        {isUserAnswer && !isCorrectOption && (
                          <span className="option-indicator">✗ Your Answer</span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {question.wrong_on_first_try && !question.is_correct && (
                  <div className="first-try-warning">
                    ⚠️ Answered incorrectly on first attempt
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="report-actions">
        <button className="btn btn-primary" onClick={onNewQuiz}>
          🔄 Start New Quiz
        </button>
      </div>
    </div>
  );
};
