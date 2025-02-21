import React from 'react';
import { Global, css } from '@emotion/react';
import Demo from './components/Demo';

const globalStyles = css`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }

  body {
    background: #f5f5f5;
    color: #333;
    line-height: 1.5;
  }

  #root {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
`;

const App: React.FC = () => {
  return (
    <>
      <Global styles={globalStyles} />
      <Demo />
    </>
  );
};

export default App;
