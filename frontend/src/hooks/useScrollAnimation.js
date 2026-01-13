import { useEffect, useRef, useState } from 'react';

/**
 * Custom hook for scroll-triggered animations using Intersection Observer.
 *
 * @param {Object} options
 * @param {number} options.threshold - Percentage of element visible to trigger (0-1, default 0.1)
 * @param {boolean} options.triggerOnce - Only trigger animation once (default true)
 * @returns {{ ref: React.RefObject, isVisible: boolean }}
 */
export function useScrollAnimation({ threshold = 0.1, triggerOnce = true } = {}) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          if (triggerOnce) {
            observer.unobserve(element);
          }
        } else if (!triggerOnce) {
          setIsVisible(false);
        }
      },
      { threshold }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [threshold, triggerOnce]);

  return { ref, isVisible };
}

/**
 * Hook for animating multiple items with staggered delays.
 * Returns an array of { ref, isVisible, style } for each item.
 *
 * @param {number} count - Number of items to animate
 * @param {Object} options
 * @param {number} options.threshold - Percentage visible to trigger (default 0.1)
 * @param {number} options.staggerDelay - Delay between each item in ms (default 100)
 * @returns {Array<{ ref: React.RefObject, isVisible: boolean, style: Object }>}
 */
export function useStaggeredAnimation(count, { threshold = 0.1, staggerDelay = 100 } = {}) {
  const refs = useRef([]);
  const [visibleItems, setVisibleItems] = useState(new Set());

  // Ensure refs array has correct length
  if (refs.current.length !== count) {
    refs.current = Array(count).fill(null).map((_, i) => refs.current[i] || { current: null });
  }

  useEffect(() => {
    const observers = [];

    refs.current.forEach((ref, index) => {
      if (!ref.current) return;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setVisibleItems(prev => new Set([...prev, index]));
            observer.unobserve(entry.target);
          }
        },
        { threshold }
      );

      observer.observe(ref.current);
      observers.push(observer);
    });

    return () => observers.forEach(obs => obs.disconnect());
  }, [count, threshold]);

  return refs.current.map((ref, index) => ({
    ref,
    isVisible: visibleItems.has(index),
    style: { animationDelay: `${index * staggerDelay}ms` }
  }));
}
