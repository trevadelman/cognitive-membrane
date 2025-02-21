import React, { useState, useEffect } from 'react';
import styled from '@emotion/styled';
import ActivityIntensity from './ActivityIntensity';
import { ActivityPattern } from '../types';

const Container = styled.div`
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20px;
`;

const generateSamplePatterns = (count: number): ActivityPattern[] => {
  const patterns: ActivityPattern[] = [];
  const now = new Date();
  
  for (let i = 0; i < count; i++) {
    const startTime = new Date(now.getTime() - (30 - i) * 60000); // Last 30 minutes
    const endTime = new Date(startTime.getTime() + 60000); // 1 minute duration
    
    // Generate a wave-like intensity pattern
    const intensity = Math.abs(Math.sin(i / 5)) * 0.8 + 0.2;
    
    patterns.push({
      pattern_type: Math.random() > 0.5 ? 'typing' : 'tool',
      start_time: startTime,
      end_time: endTime,
      intensity,
      confidence: 0.8 + Math.random() * 0.2,
      metrics: {
        avg_speed: 60 + Math.random() * 20,
        consistency: 0.7 + Math.random() * 0.3,
        burst_count: Math.floor(3 + Math.random() * 5)
      }
    });
  }
  
  return patterns;
};

const Demo: React.FC = () => {
  const [patterns, setPatterns] = useState<ActivityPattern[]>([]);
  
  useEffect(() => {
    // Initial patterns
    setPatterns(generateSamplePatterns(30));
    
    // Update patterns every 5 seconds
    const interval = setInterval(() => {
      setPatterns(prev => {
        const now = new Date();
        const newPattern: ActivityPattern = {
          pattern_type: Math.random() > 0.5 ? 'typing' : 'tool',
          start_time: new Date(now.getTime() - 60000),
          end_time: now,
          intensity: Math.abs(Math.sin(now.getTime() / 5000)) * 0.8 + 0.2,
          confidence: 0.8 + Math.random() * 0.2,
          metrics: {
            avg_speed: 60 + Math.random() * 20,
            consistency: 0.7 + Math.random() * 0.3,
            burst_count: Math.floor(3 + Math.random() * 5)
          }
        };
        
        // Remove patterns older than 30 minutes
        const cutoff = new Date(now.getTime() - 30 * 60000);
        const filtered = prev.filter(p => p.end_time > cutoff);
        
        return [...filtered, newPattern];
      });
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  const handlePatternClick = (pattern: ActivityPattern) => {
    console.log('Pattern clicked:', pattern);
  };
  
  return (
    <Container>
      <ActivityIntensity
        patterns={patterns}
        onPatternClick={handlePatternClick}
      />
    </Container>
  );
};

export default Demo;
