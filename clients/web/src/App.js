import { BrowserRouter as Router, Switch, Redirect, Route } from "react-router-dom"
import { Reader } from "./reader/Reader"

export const App = () => (
   <div className="App">
      <Router>
         <Switch>
            <Route path="/reader" component={Reader} />
            <Route path="/">
               <Redirect to="/reader/all" />
            </Route>
         </Switch>
      </Router>
   </div >
)
