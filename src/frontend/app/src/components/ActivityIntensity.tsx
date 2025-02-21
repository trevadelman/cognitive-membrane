import React, { useState, useEffect } from 'react';
import styled from '@emotion/styled';
import { motion, AnimatePresence } from 'framer-motion';
import HeatMap from './HeatMap';
import { ActivityPattern } from '../types';

interface ActivityIntensityProps {
  patterns: ActivityPattern[];
  onPatternClick?: (pattern: ActivityPattern) => void;
}

const Container = styled(motion.div)`
  position: relative;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  padding: 20px;
  margin: 20px;
  overflow: hidden;
`;

const Title = styled.h2`
  font-size: 18px;
  color: #333;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const Legend = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  font-size: 14px;
  color: #666;
`;

const LegendItem = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
`;

const LegendColor = styled.div<{ color: string }>`
  width: 12px;
  height: 12px;
  border-radius: 3px;
  background-color: ${props => props.color};
  opacity: 0.8;
`;

const ActivityIntensity: React.FC<ActivityIntensityProps> = ({
  patterns,
  onPatternClick
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Animate in after mount
    setIsVisible(true);
  }, []);

  return (
    <AnimatePresence>
      {isVisible && (
        <Container
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <Title>
            Activity Intensity
            <motion.span
              initial={{ opacity: 0.5 }}
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
              style={{ fontSize: '12px', color: '#666' }}
            >
              Live
            </motion.span>
          </Title>

          <HeatMap
            patterns={patterns}
            width={800}
            height={400}
          />

          <Legend>
            <LegendItem>
              <LegendColor color="#ff4d4d" />
              High Intensity
            </LegendItem>
            <LegendItem>
              <LegendColor color="#ffad4d" />
              Medium Intensity
            </LegendItem>
            <LegendItem>
              <LegendColor color="#4dff4d" />
              Low Intensity
            </LegendItem>
          </Legend>
        </Container>
      )}
    </AnimatePresence>
  );
};

export default ActivityIntensity;
