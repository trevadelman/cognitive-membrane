import React, { useEffect, useRef } from 'react';
import styled from '@emotion/styled';
import * as d3 from 'd3';
import { ActivityPattern } from '../types';

interface HeatMapProps {
  patterns: ActivityPattern[];
  width?: number;
  height?: number;
}

const HeatMapContainer = styled.div`
  position: relative;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  overflow: hidden;
`;

const HeatMap: React.FC<HeatMapProps> = ({
  patterns,
  width = 900,
  height = 600
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !patterns.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    // Calculate time range
    const now = new Date();
    const timeRange = [
      d3.min(patterns, p => p.start_time) || d3.timeMinute.offset(now, -30),
      d3.max(patterns, p => p.end_time) || now
    ];

    // Create scales
    const xScale = d3.scaleTime()
      .domain(timeRange)
      .range([50, width - 20]);

    const yScale = d3.scaleLinear()
      .domain([0, 1]) // Intensity range
      .range([height - 40, 20]);

    // Create axes
    const xAxis = d3.axisBottom<Date>(xScale)
      .ticks(10)
      .tickFormat(d3.timeFormat('%H:%M'));

    const yAxis = d3.axisLeft<number>(yScale)
      .ticks(5)
      .tickFormat(d => `${Math.round(d * 100)}%`);

    // Draw axes
    svg.append('g')
      .attr('transform', `translate(0, ${height - 40})`)
      .call(xAxis as any);

    svg.append('g')
      .attr('transform', 'translate(50, 0)')
      .call(yAxis as any);

    // Create heat gradient
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', 'heat-gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#ff4d4d')
      .attr('stop-opacity', 0.8);

    gradient.append('stop')
      .attr('offset', '50%')
      .attr('stop-color', '#ffad4d')
      .attr('stop-opacity', 0.6);

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#4dff4d')
      .attr('stop-opacity', 0.4);

    // Draw activity patterns
    const area = d3.area<ActivityPattern>()
      .x(d => xScale(d.start_time))
      .y0(height - 40)
      .y1(d => yScale(d.intensity))
      .curve(d3.curveBasis);

    svg.append('path')
      .datum(patterns)
      .attr('fill', 'url(#heat-gradient)')
      .attr('d', area);

    // Add interaction overlay
    const overlay = svg.append('rect')
      .attr('class', 'overlay')
      .attr('x', 50)
      .attr('y', 20)
      .attr('width', width - 70)
      .attr('height', height - 60)
      .attr('fill', 'none')
      .attr('pointer-events', 'all');

    // Add tooltip
    const tooltip = d3.select(svgRef.current.parentNode as HTMLElement)
      .append('div')
      .attr('class', 'tooltip')
      .style('opacity', 0)
      .style('position', 'absolute')
      .style('background', 'rgba(255, 255, 255, 0.9)')
      .style('padding', '8px')
      .style('border-radius', '4px')
      .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')
      .style('font-size', '12px')
      .style('pointer-events', 'none');

    // Add hover interaction
    overlay
      .on('mousemove', (event) => {
        const [x] = d3.pointer(event);
        const time = xScale.invert(x);
        
        // Find nearest pattern
        const pattern = patterns.find(p => 
          time >= p.start_time && time <= p.end_time
        );

        if (pattern) {
          tooltip
            .style('opacity', 1)
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY - 10}px`)
            .html(`
              <strong>${pattern.pattern_type}</strong><br/>
              Intensity: ${Math.round(pattern.intensity * 100)}%<br/>
              Confidence: ${Math.round(pattern.confidence * 100)}%<br/>
              ${d3.timeFormat('%H:%M:%S')(pattern.start_time)} - 
              ${d3.timeFormat('%H:%M:%S')(pattern.end_time)}
            `);
        } else {
          tooltip.style('opacity', 0);
        }
      })
      .on('mouseleave', () => {
        tooltip.style('opacity', 0);
      });

  }, [patterns, width, height]);

  return (
    <HeatMapContainer>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ display: 'block' }}
      />
    </HeatMapContainer>
  );
};

export default HeatMap;
