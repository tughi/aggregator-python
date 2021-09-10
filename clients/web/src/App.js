import { BrowserRouter as Router, Switch, Redirect, Route } from "react-router-dom"
import { Reader } from "./Reader"

export const App = () => (
   <div className="App">
      <Router>
         <Switch>
            <Route path="/reader/all" component={Reader} />
            <Route path="/reader/starred" component={Reader} />
            <Route path="/reader/feeds/:feedId" component={Reader} />
            <Route path="/">
               <Redirect to="/reader/all" />
            </Route>
         </Switch>
      </Router>
   </div >
)
